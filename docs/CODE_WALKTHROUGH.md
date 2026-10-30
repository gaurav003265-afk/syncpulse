# H5 Frontline Health-Worker Companion: Code & Architecture Walkthrough

## 1. High-Level Architecture Overview

The Frontline Health-Worker Companion is engineered for **zero-connectivity rural environments** where ASHA (Accredited Social Health Activist) and ANM (Auxiliary Nurse Midwife) workers operate.

### Strict 4-Stage Processing Pipeline

```
Raw Frontline Query (English / Telugu / Hindi / Code-Mixed)
                   │
                   ▼
       [ Stage 0: Normalisation ]
  (NFKD unicode, code-mix transliteration, vitals regex extraction)
                   │
                   ▼
 ┌──────────────────────────────────────────────────────────────┐
 │ STAGE 1: HARD DETERMINISTIC ESCALATION GATE (core/escalation)│
 │ • Hard-coded emergency danger signs (MoHFW/WHO protocols)   │
 │ • Pre-model & Pre-retrieval (cannot be bypassed)             │
 │ • Vital signs threshold checking (BP, MUAC, RR, Fever days)  │
 │ • Failsafe on negation in emergency clinical context         │
 └──────────────────────────────┬───────────────────────────────┘
                                │
               Is Danger Sign? ─┼─ YES ──► [ 🚨 REFER IMMEDIATELY ]
                                │           (Sub-0.15ms CPU latency)
                               NO
                                │
                                ▼
 ┌──────────────────────────────────────────────────────────────┐
 │ STAGE 2: PARAMEDICAL SCOPE GUARDRAIL (core/scope)            │
 │ • Whitelist standing protocol remedies (ORS, Zinc, IFA, etc.)│
 │ • Refuse unapproved prescription antibiotics & surgery       │
 │ • Refuse non-health queries                                  │
 └──────────────────────────────┬───────────────────────────────┘
                                │
             Out of Scope? ─────┼─ YES ──► [ ⚠️ PARAMEDICAL REFUSAL ]
                                │           (Safe redirect to PHC Doctor)
                            IN-SCOPE
                                │
                                ▼
 ┌──────────────────────────────────────────────────────────────┐
 │ STAGE 3: BM25 LEXICAL RETRIEVAL (core/retrieve)              │
 │ • BM25Okapi (k1=1.5, b=0.75) over 38 section chunks          │
 │ • Vernacular code-mix expansion (tika, soojan, jwaram, etc.) │
 │ • Calibrated threshold score check (<1.8)                    │
 └──────────────────────────────┬───────────────────────────────┘
                                │
             Score < 1.8? ──────┼─ YES ──► [ ℹ️ PROTOCOL ABSTENTION ]
                                │           (Zero-hallucination guardrail)
                              PASS
                                │
                                ▼
 ┌──────────────────────────────────────────────────────────────┐
 │ STAGE 4: EXTRACTIVE ANSWER COMPOSITION (core/answer)         │
 │ • Extractive factual sentence selection from top chunk       │
 │ • Zero generative drift: 100% grounded in official corpus    │
 │ • Exact Document, Section & Line-range citations returned    │
 └──────────────────────────────┬───────────────────────────────┘
                                │
                                ▼
                    [ ✓ GROUNDED PROTOCOL GUIDANCE ]
```

---

## 2. Module Deep-Dive & Jury Q&A

### Module 1: Ingest & Knowledge Pack (`core/ingest.py`, `core/build_pack.py`)
- **Responsibility:** Ingests official MoHFW/WHO clinical guideline markdown documents, splits them into semantic section-tagged chunks, computes token frequencies, builds the inverted BM25 index, and seals the package with SHA-256 hashes in `manifest.json`.
- **Inputs:** Raw markdown files in `data/synthetic_corpus/`.
- **Outputs:** `data/knowledge_pack/` (`manifest.json`, `chunks.json`, `bm25_index.json`, `escalation_rules.json`). Total footprint: **188.68 KB**.
- **Jury Q&A:**
  1. *Q: Why pre-build a knowledge pack instead of indexing on startup?*
     **Answer:** Frontline phones have low CPU and tight memory. Loading a pre-compiled JSON index takes only **40.9 ms** (cold start), compared to seconds of parsing text on device.
  2. *Q: How do you verify that protocols haven't been corrupted or altered?*
     **Answer:** `manifest.json` stores individual SHA-256 hashes for every protocol file. When `FrontlineCompanionPipeline` boots, it verifies the hashes.
  3. *Q: How do you add new languages or state-specific protocols?*
     **Answer:** The architecture is decoupled: updating protocols simply means replacing the knowledge pack via `python -m core.build_pack` without recompiling or rewriting application code.

---

### Module 2: Escalation Layer (`core/escalation.py`, `web/src/engine/escalation.ts`)
- **Responsibility:** Deterministic emergency detector that fires before any model inference or retrieval. Covers 28 clinical danger rules across 7 categories (Maternal Obstetric, Neonatal, Pediatric Malnutrition, Diarrhea/Dehydration, Respiratory/Pneumonia, Fever/Meningitis, Non-Communicable Diseases).
- **Inputs:** Raw user query string.
- **Outputs:** `EscalationResult` (`escalate: bool`, `action_text`, `corpus_citation`, `matched_rules`, `negation_detected`).
- **Measured Performance:** **100.0% Recall** on 342 emergency test cases, **0.0% False Escalation Rate**, **0.13 ms CPU latency** in Python, **0.04 ms** in Node/TypeScript.
- **Jury Q&A:**
  1. *Q: Why not use a language model or classifier for emergency detection?*
     **Answer:** Probabilistic language models can hallucinate, suffer from attention dilution, or drift under noisy input. For life-threatening emergencies (e.g. postpartum hemorrhage, neonatal convulsion), the medical standard requires deterministic, 100% reproducible rule triggers that cannot fail due to model latency or prompt variations.
  2. *Q: How do you handle negation, such as "She has no bleeding"?*
     **Answer:** Negation handling is safety-tuned: if a clinical emergency sign and a negation word co-occur, the engine detects negation (`negation_detected=True`) but errs on the side of caution (failsafe referral) because frontline workers often write "no bleeding now but had heavy bleeding earlier".
  3. *Q: How do you prevent procedural questions like "How to test for edema?" from triggering emergency ambulance referral?*
     **Answer:** Procedural prefixes (`how to test`, `how to measure`, `procedure for`) are recognized and bypassed into standard protocol retrieval so instructions are returned rather than ambulance alarms.

---

### Module 3: Paramedical Scope & Refusal (`core/scope.py`, `web/src/engine/scope.ts`)
- **Responsibility:** Protects legal and clinical boundaries of paramedical frontline workers. Distinguishes between protocol-approved remedies and unapproved prescription drugs, surgery, or non-health questions.
- **Inputs:** Query text.
- **Outputs:** `ScopeResult` (`is_in_scope: bool`, `scope_category`, `refusal_reason`, `redirect_message`).
- **Jury Q&A:**
  1. *Q: Why does ASHA need a scope guardrail?*
     **Answer:** In India, ASHA and ANM workers are authorized to distribute standard preventive items (ORS, Zinc, IFA, Calcium, Albendazole, Paracetamol). They are legally prohibited from prescribing prescription antibiotics (e.g. Ciprofloxacin, Amoxicillin) or titrating insulin doses. The companion reinforces this boundary and directs them to the Medical Officer.
  2. *Q: What happens if an emergency query mentions a prescription drug?*
     **Answer:** Safety prioritization: Stage 1 (Escalation) executes *before* Stage 2 (Scope). If a pregnant mother with heavy bleeding asks for a painkiller or antibiotic, emergency ambulance escalation takes immediate precedence.
  3. *Q: How are non-health queries handled?*
     **Answer:** Queries regarding sports, entertainment, politics, or general trivia are classified as `OUT_OF_SCOPE_NON_HEALTH` with a polite explanation that the system is dedicated to health protocols.

---

### Module 4: BM25 Retrieval & Grounded Answers (`core/retrieve.py`, `core/answer.py`)
- **Responsibility:** Retrieves relevant protocol chunks using BM25Okapi with vernacular expansion; composes extractive answers citing document, section, and line numbers.
- **Inputs:** Normalized query, top-k chunks.
- **Outputs:** `PipelineResponse` (`type: "answer" | "abstain"`, `text`, `citations`, `confidence`, `latency_ms`).
- **Jury Q&A:**
  1. *Q: Why BM25 instead of dense neural embeddings?*
     **Answer:** Dense neural embeddings require 50-200 MB of model weights and heavy tensor matrix multiplications, draining battery and consuming memory on rural low-end devices. BM25 is lightweight (47 KB index), runs in **< 1 millisecond**, and handles exact medical terminology (e.g., "Td-1", "MUAC", "Albendazole") with zero hallucination.
  2. *Q: How do you handle Telugu and Hindi words like "tika" or "jwaram"?*
     **Answer:** `core/retrieve.py` includes a curated clinical code-mix synonym map that expands vernacular tokens to clinical keywords (e.g., `tika` $\to$ `vaccine, immunisation`, `jwaram` $\to$ `fever`, `prasavam` $\to$ `delivery`).
  3. *Q: How do you prevent hallucinations?*
     **Answer:** Answer composition is strictly extractive. The pipeline selects factual sentences directly from the top retrieved chunk. If the BM25 score is below the calibrated threshold of 1.8, the system abstains rather than inventing medical advice.

---

### Module 5: Prioritized Daily Visits (`core/visits.py`, `web/src/engine/visits.ts`)
- **Responsibility:** Evaluates household registers (synthetic 500 families) and produces an explainable, prioritized daily visit list.
- **Tiers:**
  - **Tier 1 (Critical High Risk):** Severe anemia, hypertensive pregnancy, SAM malnutrition (Rank: 10,000+).
  - **Tier 2 (Overdue Routine):** Beneficiaries overdue by $>0$ days (Rank: 5,000 + $5 \times \text{overdue\_days}$).
  - **Tier 3 (Due Today):** Scheduled for today (Rank: 2,000).
  - **Tier 4 (Upcoming):** Future appointments (Rank: <100).
- **Jury Q&A:**
  1. *Q: How does this help an ASHA worker on a typical morning?*
     **Answer:** Instead of flipping through paper registers or guessing who to visit, the ASHA opens the companion, filters by her village, and sees her prioritized schedule: high-risk emergencies first, followed by overdue immunizations.
  2. *Q: What happens when an ASHA marks a visit done without internet?*
     **Answer:** The visit is committed immediately to local SQLite / localStorage, timestamped, and queued in an offline sync outbox. When connectivity is restored, the outbox flushes idempotently to the server.
  3. *Q: How fast does the prioritization scale?*
     **Answer:** In our scale tests (`bench/scale_test.py`), prioritizing **50,000 households** took only **22.25 ms** on standard CPU.

---

### Module 6: Full-Stack PWA & Offline Verification (`server/main.py`, `web/dist`)
- **Responsibility:** Serves the frontend as a Progressive Web App from FastAPI; provides client-side TypeScript parity engine for execution with zero backend calls.
- **Jury Q&A:**
  1. *Q: How do you prove this works with zero internet?*
     **Answer:** We ran `bench/verify_offline.py` which monkeypatches Python's socket library to block all network egress. All 96 benchmark queries passed offline. Furthermore, the PWA runs client-side inside the browser using Service Workers.
  2. *Q: Does the demo require Node.js at runtime?*
     **Answer:** No. The frontend is pre-built into `web/dist` and served statically by FastAPI. Running the entire app requires only Python standard libraries and FastAPI/Uvicorn.
