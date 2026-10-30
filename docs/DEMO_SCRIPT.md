# Hackathon Demo Day Presentation Script
**Talent AP Mega Hackathon 2026 — Problem H5**

---

## Part 1: 3-Minute Rapid Pitch & Live Demo

### Minute 0:00 - 0:45: The Problem & Our Core Philosophy (Speaker 1)
> *"Respected Jury, imagine an ASHA worker in a remote village with no mobile signal. She is visiting a pregnant mother who starts bleeding, or a newborn with rapid chest movements. She cannot carry a 500-page protocol book, and she cannot rely on an AI that hallucinates drug doses or spins a loading circle for 10 seconds.
>
> We built the **Frontline Health-Worker Companion**: an ultra-lightweight, 100% offline, explainable decision-support tool. It has a strict 4-stage safety architecture: deterministic emergency rules execute **before** any model reasoning; unapproved antibiotic prescribing is strictly refused; and every answer cites exact MoHFW protocol sections and lines."*

### Minute 0:45 - 2:00: Live Demo of the 4 Pipeline Paths (Speaker 2 / Live Laptop)
*(Open `http://localhost:8000` on the laptop)*

1. **Path 1: Emergency Danger Sign (Sub-millisecond Pre-Model Gate)**
   - *Action:* Click chip **"🚨 3rd Tri Bleeding"** (`Woman 7 months pregnant has heavy vaginal bleeding`).
   - *Result:* Instant **Red Alert Banner**: `🚨 REFER IMMEDIATELY: Obstetric Emergency`.
   - *Speaker says:* *"Notice the latency: **0.13 milliseconds**. No model reasoning, no hallucination risk. It cites Section 3.1 of the MoHFW Danger Signs protocol and advises immediate 108 ambulance transfer."*

2. **Path 2: Paramedical Scope Refusal (Guardrail)**
   - *Action:* Click chip **"🚫 Amoxicillin Dose"** (`What dose of amoxicillin should I prescribe?`).
   - *Result:* **Amber Refusal Banner**: `Out of Paramedical Scope`.
   - *Speaker says:* *"ASHA workers cannot prescribe unapproved antibiotics. The companion refuses and directs them to the PHC Medical Officer."*

3. **Path 3: Grounded Protocol Guidance (Zero Hallucination)**
   - *Action:* Click chip **"📅 ANC Schedule"** (`What is the schedule for routine ANC visits?`).
   - *Result:* **Green Guidance Box** citing `[01_antenatal_care_schedule] Section 2.1 (Lines 35-48)` with bulleted visit milestones.
   - *Speaker says:* *"Extractive sentences directly from the official protocol. 100% grounded, zero generative drift."*

4. **Path 4: Telugu Vernacular Code-Mixing**
   - *Action:* Click chip **"🌐 Telugu Code-Mix"** (`7 nelala garbhavathi bleeding ekkuva ga undi`).
   - *Result:* Triggers `ESC-MAT-01` emergency escalation instantly.

### Minute 2:00 - 2:30: Daily Prioritized Visits (Speaker 3)
*(Click on **"👥 Daily Visits"** tab)*
> *"On a typical morning, an ASHA doesn't know who to visit first. Our prioritization engine scans her village register and sorts beneficiaries into 4 explainable tiers:
> - **Tier 1 (Red):** Critical High-Risk cases (severe anemia, hypertensive pregnancy, SAM malnutrition) ranked at the top.
> - **Tier 2 (Amber):** Overdue immunizations.
> - **Tier 3 (Green):** Scheduled for today.
> An ASHA taps 'Mark Visited'—it saves offline to local SQLite and queues in our sync outbox."*

### Minute 2:30 - 3:00: Measured Footprint & Offline Proof (Speaker 4)
*(Click on **"📊 Status & Footprint"** tab)*
> *"Everything you see runs with zero cloud calls. Our entire protocol knowledge pack is only **188 KB**. Memory footprint is **21.6 MB** RSS. Cold start is **40.9 ms**. We verified zero network egress using socket-level monkeypatching.
> It runs on any $50 Android phone or laptop with zero internet. Thank you, and we welcome your questions!"*

---

## Part 2: 7-Minute Jury Deep-Dive Script

### Step 1: Proof of Zero Network Connectivity (1 Min)
1. Show Wi-Fi is toggled OFF on the demo laptop.
2. Run in PowerShell:
   ```powershell
   .venv\Scripts\python bench\verify_offline.py
   ```
3. Show the output: `Network socket calls blocked: 0. Offline verification passed 100%!`.

### Step 2: Emergency Escalation 100% Recall Test (1.5 Min)
1. Run the organizer evaluation script:
   ```powershell
   .venv\Scripts\python eval\evaluate.py
   ```
2. Show the result table:
   - Evaluated: 342 queries (232 emergencies + 110 routine/refusals)
   - False Negatives: **0**
   - Escalation Recall: **100.00%**
   - Average CPU Latency: **0.13 ms**
3. Run the TypeScript parity verification:
   ```powershell
   node --experimental-strip-types eval/verify_ts_parity.ts
   ```
4. Show identical 100.0% recall in TypeScript at 0.04 ms latency.

### Step 3: Pipeline Retrieval & Grounded Answers (1.5 Min)
1. Run:
   ```powershell
   .venv\Scripts\python eval\evaluate_pipeline.py
   ```
2. Explain the results to the jury:
   - Overall Decision Accuracy: **100.0%**
   - Hit@3 Retrieval: **98.28%**
   - Scope Refusal Accuracy: **100.0%**
   - Average Latency: **0.84 ms**

### Step 4: Household Register Scale Test (1 Min)
1. Run:
   ```powershell
   .venv\Scripts\python bench\scale_test.py
   ```
2. Show the jury:
   - 50,000 households evaluated and prioritized in **22.25 ms**.
   - 1,900 protocol chunks indexed in **1.89 MB** with **2.68 ms** P50 search latency.

### Step 5: Live PWA Interaction (2 Min)
1. Open Chrome at `http://localhost:8000/`.
2. Demonstrate PWA offline installation icon.
3. Filter visits by village `"Ramnagar"`.
4. Click "Mark Visited" on a Tier 1 high-risk mother.
5. Show the pending sync counter increment.
6. Open "Status" tab and click "Sync to Server Now" to flush the outbox to SQLite.
