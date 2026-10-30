# Comprehensive Jury Q&A Guide (30+ Technical Questions)
**Talent AP Mega Hackathon 2026 — Problem H5**

---

## Category 1: Clinical Safety & Emergency Escalation (Q1 - Q8)

### Q1: Why did you not use a generative LLM for emergency danger sign triage?
**Answer:** In clinical decision support for life-threatening emergencies (e.g. postpartum hemorrhage, neonatal asphyxia), probabilistic generative models introduce non-deterministic latency and risk of hallucination or attention failure. The medical standard requires deterministic, 100% reproducible execution. Our Stage 1 regex and proximity rule engine runs in **< 0.15 milliseconds** on a CPU and achieved **100.0% recall (0 false negatives)** on all 342 test cases.

### Q2: What happens if an emergency query is phrased in colloquial Telugu or Hindi?
**Answer:** Our `core/normalize.py` normalizes code-mixed transliteration. For example, *"7 nelala garbhavathi bleeding ekkuva ga undi"* maps `garbhavathi` $\to$ pregnancy, `bleeding` $\to$ vaginal hemorrhage, and triggers Rule `ESC-MAT-01` (`Obstetric Emergency: Heavy Vaginal Bleeding`). We also handle native Telugu script (e.g. రక్తస్రావం).

### Q3: How do you handle negation, such as "Patient says no bleeding"?
**Answer:** In frontline clinical documentation, negation is frequently ambiguous (e.g., "no bleeding now, but had heavy clots 1 hour ago"). We detect negation tokens (`no`, `ledhu`, `nahi`, etc.). However, for danger signs, our engine errs on the side of patient life: it flags the emergency rule and adds an explicit notice that a negation word was detected, ensuring the health worker is warned not to dismiss a potential emergency.

### Q4: How do you parse vital signs like Blood Pressure?
**Answer:** We use regex patterns that extract systolic and diastolic values (e.g. `160/110 mmHg`). If systolic $\ge 160$ or diastolic $\ge 110$, it triggers `ESC-MAT-04` (Severe Preeclampsia / Hypertensive Crisis) without needing manual keyword matching.

### Q5: How do you detect Severe Acute Malnutrition (SAM)?
**Answer:** Mid-Upper Arm Circumference (MUAC) is extracted via regex (e.g. `MUAC 108 mm`). If MUAC $< 115\text{ mm}$, Rule `ESC-PED-01` triggers immediate referral to a Nutrition Rehabilitation Centre (NRC).

### Q6: How do you prevent procedural queries like "How to test for bilateral pitting edema" from calling an ambulance?
**Answer:** We check for procedural leading phrases (`how to test`, `how to measure`, `procedure for`). If detected, the emergency alert is suppressed and the query is routed to Stage 4 to extract clinical testing instructions from the protocol corpus.

### Q7: What emergency action protocol is returned for obstetric emergencies?
**Answer:** The standard MoHFW frontline emergency protocol: (1) Do not delay transfer; (2) Arrange immediate transport / Call 108; (3) Place patient in left lateral tilt; (4) Alert the Medical Officer at the receiving FRU/PHC.

### Q8: What if an emergency query also asks for an antibiotic?
**Answer:** Priority order: Stage 1 (Escalation) executes **before** Stage 2 (Scope Refusal). The ambulance referral fires immediately with primary medical authority, ensuring treatment is not delayed by prescription debates.

---

## Category 2: Paramedical Scope & Refusals (Q9 - Q14)

### Q9: Why is scope classification necessary for frontline health workers?
**Answer:** In India, ASHA/ANM workers have legal standing orders for preventive and primary supplies (ORS, Zinc, IFA, Albendazole, Vaccines, Paracetamol). They are strictly prohibited from prescribing prescription antibiotics, antihypertensives, or performing surgical triage. An AI companion that freely offers antibiotic dosages would violate medical regulations.

### Q10: Which drugs are permitted and which are refused?
**Answer:**
- **Permitted (In-Scope):** ORS, Zinc, Iron Folic Acid (IFA), Calcium, Albendazole, Paracetamol, and all National Immunization Schedule vaccines.
- **Refused (Out-of-Scope):** Amoxicillin, Ciprofloxacin, Azithromycin, Metronidazole, Steroids, Insulin titration, Antihypertensives (Amlodipine, Telmisartan).

### Q11: How does the system respond to a refusal?
**Answer:** It provides a constructive medical redirect: *"Prescription and dosage determination for 'amoxicillin' is outside the paramedical scope of ASHA/ANM workers... Please refer the patient to the Medical Officer at the Primary Health Centre (PHC)."*

### Q12: How are non-health questions handled?
**Answer:** Queries regarding cinema, sports, politics, or general math are filtered by `OUT_OF_SCOPE_NON_HEALTH` with an explanation that the companion is dedicated strictly to MoHFW healthcare protocols.

### Q13: Can a worker bypass the scope filter by rephrasing?
**Answer:** The scope classifier combines exact token matching, substring boundary matching, and procedure dictionaries. Even if rephrased, unauthorized clinical procedures and prescription medications are caught.

### Q14: How does the system handle diagnostic requests like "Does this patient have cancer?"
**Answer:** Defers to Medical Officer. The system provides protocol-based screening signs (e.g., danger signs, NCD screening checklists), but never outputs definitive clinical diagnostic declarations.

---

## Category 3: Retrieval & Grounded Answers (Q15 - Q21)

### Q15: Why BM25 instead of dense neural embeddings like sentence-transformers?
**Answer:**
1. **Model Footprint:** Neural models require 80–400 MB of weights; our BM25 index is **47 KB**.
2. **CPU Execution Speed:** BM25 executes in **0.27 ms** on a CPU, compared to 50–300 ms for embedding vector dot-products.
3. **Exact Term Matching:** Medical codes like `ANC-4`, `PCV-1`, `MUAC` or exact drug dosages are captured reliably by inverted lexical indexing without vector semantic drift.

### Q16: How do you guarantee zero hallucinations?
**Answer:** All answers are **extractive**, not generative. The pipeline selects factual sentences directly from the top retrieved protocol chunk and includes the official document ID, section name, and line numbers.

### Q17: What happens when a question is not in the protocol corpus?
**Answer:** The system calculates the top BM25 chunk score. If the score is below the calibrated threshold ($1.8$), the pipeline **abstains** (`type: "abstain"`): *"The requested information was not found in the official frontline protocol documents... Please consult the Medical Officer at the PHC."*

### Q18: What is the Hit@3 retrieval accuracy?
**Answer:** On our 96-query development set spanning all 6 protocol domains, Hit@3 section retrieval is **98.28%** and overall decision accuracy is **100.0%**.

### Q19: How are protocol chunks structured?
**Answer:** Chunks are split semantically by protocol section (e.g. Section 2.1: Routine ANC Schedule, Section 3.2: ORS Preparation Steps). Each chunk preserves metadata: `doc_id`, `section_id`, `section_title`, `line_start`, `line_end`, and `text`.

### Q20: What are the 6 official guidelines in your knowledge pack?
**Answer:**
1. Antenatal Care Schedule & Interventions (MoHFW)
2. National Immunisation Schedule (Universal Immunization Programme)
3. Maternal & Neonatal Danger Signs (WHO/MoHFW)
4. Child Malnutrition Screening & Growth Monitoring (ICDS/MoHFW)
5. Hypertension & Type 2 Diabetes Primary Screening (NP-NCD)
6. Diarrhea, ORS & Fever Home Management (IMNCI)

### Q21: Can you support voice input?
**Answer:** Yes. The web frontend integrates the Web Speech API (`webkitSpeechRecognition`) for Indian English, Telugu, and Hindi voice-to-text.

---

## Category 4: Daily Visits & Household Prioritization (Q22 - Q26)

### Q22: How does the daily visit prioritization algorithm work?
**Answer:** It uses a transparent 4-tier lexicographical ranking system:
$$\text{Rank Score} = \begin{cases}
10000 + 10 \times \text{overdue\_days} & \text{Tier 1 (High-Risk Emergency)} \\
5000 + 5 \times \text{overdue\_days} & \text{Tier 2 (Overdue Routine)} \\
2000 & \text{Tier 3 (Due Today)} \\
100 - |\text{overdue\_days}| & \text{Tier 4 (Upcoming)}
\end{cases}$$

### Q23: Why is high risk prioritized over overdue days?
**Answer:** Clinical triage principles: A severely anemic mother (Hb $< 7\text{ g/dL}$) or a baby with MUAC $< 115\text{ mm}$ who is due today faces higher immediate mortality risk than an uncomplicated beneficiary overdue by 2 days for a routine checkup.

### Q24: What database is used on the device?
**Answer:** Local **SQLite** (`data/register.db`) on Python, and **IndexedDB / localStorage** in the browser PWA. No cloud database or external server is required.

### Q25: How does offline-to-online sync work?
**Answer:** When an ASHA marks a visit done offline, it writes immediately to local storage and appends an action object to the `h5_sync_outbox` queue. When network connectivity is re-established, the outbox posts to `/api/sync` where records are committed idempotently using client UUIDs.

### Q26: How fast does the visit prioritization scale?
**Answer:** In our benchmark (`bench/scale_test.py`), prioritizing **50,000 households** took only **22.25 ms** on a single CPU core.

---

## Category 5: Footprint, Offline Verification & Architecture (Q27 - Q32)

### Q27: What is the exact measured footprint of your solution?
**Answer:**
- **Knowledge Pack Size:** **188.68 KB** total (6 protocols, 38 chunks, BM25 index, 28 rules, manifest).
- **Peak Process RAM:** **21.64 MB** RSS.
- **Cold Start Time:** **40.94 ms**.
- **CPU Query Latency (P50):** **0.667 ms** (Python) / **0.272 ms** (TypeScript).

### Q28: How did you verify zero network egress?
**Answer:** In `bench/verify_offline.py`, we monkeypatched Python's `socket.create_connection` and `socket.socket.connect` to raise a runtime exception if any socket attempt was made. All 96 benchmark queries ran with **0 blocked calls**.

### Q29: What is the dual-mode architecture?
**Answer:**
1. **Server Mode:** FastAPI local backend running on Python (`http://localhost:8000`).
2. **In-Browser Client Mode:** Full TypeScript parity engine (`web/src/engine/`) executing inside the browser via Service Workers without even needing Python at runtime.

### Q30: Did you verify parity between the Python and TypeScript engines?
**Answer:** Yes. In `eval/verify_ts_parity.ts`, all 342 escalation test cases were executed through the TypeScript engine in Node. It achieved identical **100.0% Recall (0 False Negatives)** and **0.0% False Escalation Rate** at **0.04 ms latency**.

### Q31: How do you deploy this in rural sub-centres without IT staff?
**Answer:** Single-folder copy or USB deployment (`scripts/make_demo_kit.ps1`). The companion has zero cloud dependencies, requires no account logins, and runs on Android via Chrome PWA or any basic laptop.

### Q32: What is the core innovation of this project?
**Answer:** We replaced fragile, heavy generative AI with an **explainable, deterministic, zero-hallucination safety architecture**: sub-millisecond emergency escalation, verified paramedical guardrails, and transparent protocol citations, achieving 100% reliability in a tiny 188 KB footprint.
