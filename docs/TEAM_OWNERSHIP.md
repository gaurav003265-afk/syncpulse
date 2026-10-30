# Team Ownership & Module Assignments (2 to 4 Students)
**Talent AP Mega Hackathon 2026 — Problem H5**

To present a confident, unified front to the jury, each student should own specific modules of the companion and be ready to answer technical and clinical questions.

---

## Team Setup Options

### 4-Student Configuration (Recommended)

#### Student 1: Lead Engineer & Clinical Safety Lead
- **Assigned Modules:**
  - `core/escalation.py` (Stage 1 Deterministic Danger-Sign Escalation Layer)
  - `core/normalize.py` (Linguistic preprocessing & Vitals regex extraction)
  - `data/escalation_rules.json` & `docs/ESCALATION_COVERAGE.md`
- **60-Second Pitch:**
  > *"I own the hard-gate emergency escalation system. When an ASHA worker types in an emergency symptom—like bleeding in the third trimester or a newborn with chest indrawing—our engine triggers in less than 0.15 milliseconds using deterministic clinical rules. We bypass any language model reasoning to guarantee 100% recall. On our 342-case emergency evaluation set, we achieved zero false negatives. We also safely catch vital sign thresholds like severe hypertension and SAM malnutrition."*
- **Key Jury Questions to Answer:**
  - Why deterministic rules instead of an LLM or classifier?
  - How do you handle negation like "no bleeding"?
  - How do you parse vital signs like BP 160/110 or MUAC 110 mm?

---

#### Student 2: Applied-ML & Information Retrieval Engineer
- **Assigned Modules:**
  - `core/ingest.py` & `core/build_pack.py` (Corpus Ingestion & Knowledge Pack)
  - `core/retrieve.py` (BM25 Retrieval & Vernacular Code-Mix Expansion)
  - `core/answer.py` (Extractive Grounded Answer Composition)
- **60-Second Pitch:**
  > *"I own the retrieval and grounded answer engine. Instead of a heavy embedding model that drains battery on low-end phones, we built an optimized BM25Okapi search index that takes just 47 KB. We added a Telugu and Hindi code-mix dictionary so words like 'tika' and 'soojan' match official clinical terms. Crucially, our answers are 100% extractive with line citations: we never let a model invent dosages. If a query is outside the guidelines, we cleanly abstain."*
- **Key Jury Questions to Answer:**
  - Why BM25 over dense vector embeddings for rural frontline workers?
  - How does your code-mix vernacular mapping work?
  - How do you prevent hallucinations and enforce citation accuracy?

---

#### Student 3: Paramedical Scope & Household Workflow Engineer
- **Assigned Modules:**
  - `core/scope.py` (Stage 2 Paramedical Scope & Prescription Refusal)
  - `core/visits.py` (Household Register Prioritization & Daily Visit Schedule)
  - `data/synthetic_register/` & SQLite persistence (`data/register.db`)
- **60-Second Pitch:**
  > *"I own the frontline workflow and paramedical guardrails. ASHA workers are not doctors, so our scope filter stops unapproved antibiotic prescriptions and redirects them to a PHC Medical Officer. For daily visits, our prioritization engine evaluates 500 households and ranks high-risk mothers and severe acute malnutrition cases at the very top (Tier 1), followed by overdue immunizations (Tier 2). Prioritizing 50,000 households takes only 22 milliseconds on a standard CPU."*
- **Key Jury Questions to Answer:**
  - What drugs can an ASHA recommend vs what must be refused?
  - How does the visit ranking formula balance overdue days vs medical risk?
  - How do visits sync when connectivity is restored?

---

#### Student 4: Systems, PWA & Footprint QA Engineer
- **Assigned Modules:**
  - `server/main.py` (FastAPI Server & Static PWA Mount)
  - `web/` & `web/src/engine/` (TypeScript Parity Engine & PWA UI)
  - `bench/` (`benchmark.py`, `verify_offline.py`, `scale_test.py`)
- **60-Second Pitch:**
  > *"I own system performance, offline verification, and the frontend PWA. We verified 100% offline execution by monkeypatching the OS socket layer to block network calls during evaluation. The complete knowledge pack is only 188 KB, peak RAM is 21.6 MB, and cold start is 40.9 ms. We also ported the engine to TypeScript with 100% parity so the companion runs completely inside the browser without even needing the backend server."*
- **Key Jury Questions to Answer:**
  - How do you prove this runs with zero internet?
  - What are your real measured footprint numbers?
  - How does the TypeScript engine match the Python engine?

---

### 2-Student Configuration

If presenting with a 2-student team:
- **Student A (Safety & Algorithms):** Owns Escalation (Student 1) + Retrieval/Grounded Answers (Student 2).
- **Student B (Workflows & Systems):** Owns Scope/Visits (Student 3) + Footprint/PWA/Benchmarking (Student 4).
