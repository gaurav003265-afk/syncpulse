# SyncPulse (Sakhi FieldOS) — Frontline Healthcare Field Platform
**Healthcare Connected. Even Offline.**  
**Event:** Talent AP Mega Hackathon 2026 (Healthcare Track — Problem Statement H5)  
**Target Users:** Accredited Social Health Activist (ASHA) Workers, ANMs, and Rural Community Health Supervisors

---

## 1. Project Overview

**SyncPulse (Sakhi FieldOS)** is a production-grade, offline-first mobile web application and clinical decision support system designed specifically for frontline community health workers operating in low-resource, zero-connectivity rural environments across Andhra Pradesh and India.

Frontline ASHA workers typically manage registers of 200–500 households, performing home visits, monitoring maternal and infant health, tracking immunization schedules, and identifying medical emergencies. In the field, network connectivity is notoriously unreliable (frequently 2G or zero signal), making traditional cloud-dependent mobile apps and cloud LLM APIs entirely non-viable.

SyncPulse solves this challenge with a **100% on-device, zero-hallucination, deterministic architecture**:
- **Zero-Latency Offline Execution:** Operates entirely on-device with an ultra-compact **1.58 MB total asset footprint** and **4.48 ms cold-start latency**.
- **100% Recall Emergency Safety Gate:** Deterministic regex and clinical keyword triage intercepts critical emergencies in **0.89 ms**, enforcing immediate 108 ambulance referral before any retrieval or language model can introduce delay or hallucination.
- **Explainable Clinical Retrieval:** Grounded strictly in official Ministry of Health and Family Welfare (MoHFW) and WHO protocols with mandatory document title, chapter, and page citations.
- **Frontline Paramedical Scope Guard:** Deterministically refuses unauthorized requests to prescribe scheduled antibiotics or medications beyond an ASHA worker's legal mandate.
- **Relational Field Data Engine:** Full offline ACID SQLite database managing 500 households, maternal/child beneficiaries, clinical visit outcomes, high-risk flags, and straight-line proximity radar.

---

## 2. System Architecture & Escalation Pipeline

```mermaid
flowchart TD
    User(["Frontline Health Worker (ASHA) / Community User"]) --> Input["User Query (Typed or Offline Voice)"]
    
    subgraph S1 ["Stage 1: Pre-Inference Hard Safety Gate (< 1 ms)"]
        Input --> GateCheck{"Matches Critical Obstetric or Pediatric Red Flags?"}
        GateCheck -->|"YES (Critical Emergency)"| RedAlert["Deterministic Red Emergency Card\n• Immediate 108 Ambulance Action\n• Emergency First-Aid Guidelines\n• Auto-Log to Local Emergency Desk"]
        RedAlert --> LocalOutbox["Local SQLite Outbox (Audit Trail)"]
    end

    subgraph S2 ["Stage 2: Paramedical Scope Gate"]
        GateCheck -->|"NO"| ScopeCheck{"Asks for Scheduled Prescription / Antibiotics?"}
        ScopeCheck -->|"YES (Out of Scope)"| Refusal["Deterministic Scope Refusal Card\n• Frontline Health Workers Cannot Prescribe\n• Refer to PHC Medical Officer"]
    end

    subgraph S3 ["Stage 3: Vectorless Protocol Retrieval"]
        ScopeCheck -->|"NO (Routine Clinical Question)"| BM25["Deterministic BM25Okapi Engine\n• 58 Official MoHFW/WHO Chunks\n• Exact Term Frequency & Inverted Index\n• Zero Vector Embedding Overhead"]
    end

    subgraph S4 ["Stage 4: Extractive Protocol Adapter"]
        BM25 --> Adapter["Zero-Shot Extractive Adapter\n• Extracts Verbatim Grounded Guidance\n• Validates Substring Consistency\n• Attaches Document, Chapter & Page Citations"]
        Adapter --> AnswerCard["Explainable Protocol Guidance Card\n• Step-by-Step Clinical Actions\n• Official Protocol Citation Badge\n• 'Cure Window' First-Aid Link"]
    end

    subgraph LocalStorage ["On-Device Persistent Data Layer"]
        LocalOutbox <--> SQLite["SQLite 3 WAL Database (500 Households)\n• ACID Transactions\n• Visit Outcomes & Follow-ups\n• Haversine Distance Radar"]
    end
```

### The 4-Stage Clinical Safety Pipeline Explained

1. **Stage 1 — Deterministic Emergency Gate (0.89 ms):** Evaluates incoming text against 58 high-risk clinical triggers (e.g., eclampsia, antepartum hemorrhage, severe respiratory distress, neonate hypothermia). Achieves **100.0% Recall (0 False Negatives)** on benchmark evaluations. It routes immediately to life-saving action instructions and dials `108` without touching an LLM.
2. **Stage 2 — Paramedical Scope Guard:** Protects public health against improper antibiotic stewardship and illegal medical prescriptions. Any prompt asking for drug dosages (e.g., *Amoxicillin*, *Ciprofloxacin*, *Metronidazole*) is blocked with an explanation that ASHAs must refer patients to a Medical Officer at the Primary Health Centre (PHC).
3. **Stage 3 — Vectorless BM25Okapi Retrieval:** Indexes 58 chunked guidelines from official Indian health authorities. BM25 scoring runs purely in CPU memory with zero floating-point embedding model overhead, executing top-3 retrieval in **under 2 milliseconds**.
4. **Stage 4 — Extractive Protocol Adapter:** Generates structured, evidence-grounded instructions by extracting relevant protocol sections, verifying that clinical terminology matches the source documents, and appending mandatory citations (e.g., `MoHFW Maternal Health Protocols, Section 4.2, Page 18`).

---

## 3. Main Features

### 1. Unified Search — Ask Sakhi
- Accepts text input and verified speech input via the Web Speech API.
- Immediate response categorization: **Emergency Escalation**, **Verified Protocol Guidance**, **Nuanced Non-Emergency Referral**, or **Scope Refusal**.
- Quick-filter symptom prompt chips for common rural field scenarios.

### 2. Household Register & Beneficiary Profiles (500 Records)
- Pre-loaded with the complete 500-household synthetic field register in a normalized SQLite database.
- Searchable by household ID (`HH-0001` to `HH-0500`), beneficiary name, village, or head of household.
- Categorized by beneficiary cohorts: **Maternal (Pregnant/Lactating)**, **Infant (0–1 yr)**, **Child (1–5 yrs)**, **Adolescent**, and **Adult NCD (Hypertension/Diabetes)**.
- Color-coded badges indicating high-risk pregnancies, severe anemia, malnutrition, and uncontrolled hypertension.

### 3. Visit Planner & Haversine Distance Radar
- Dynamically organizes visits into **Due Today**, **Overdue**, **Upcoming**, and **High-Risk**.
- Calculates straight-line distance locally using the Haversine formula ($R = 6371\text{ km}$) from frontline worker coordinates to household coordinates.
- Supports GPS coordinate capture and manual coordinate entry/correction.
- **Transparent Distance Labeling:** Strictly labeled as *"Straight-line distance"* to avoid misleading workers regarding actual road travel times.

### 4. Clinical Visit Outcome Recording
- Record vital signs during household visits: Blood Pressure (Systolic/Diastolic), Pulse, Body Temperature, Weight, and MUAC (Mid-Upper Arm Circumference).
- Dropdown selection of services rendered (e.g., *IFA Tablets Distributed*, *Immunization Verification*, *Nutrition Counseling*).
- Atomically saves records to local SQLite and appends tasks to the follow-up planner.

### 5. Emergency Safety Desk & Audit Logging
- Real-time triage log of all critical emergency events raised during field visits or queries.
- Clearly displays severity, detected symptoms, and recommended escalation protocol.
- **Honest Delivery Status:** Alerts are tagged with transparent delivery states (`Saved Locally (On-Device Only) • Notification Service Not Configured` vs `Sent Successfully`) to prevent false assumptions that an offline alert dispatched an ambulance.

### 6. The Cure Window (First Aid & Referral Protocols)
- Rapid step-by-step first-aid guidance for acute field situations:
  - **Burns & Scalds:** Cool water irrigation, dry sterile covering, chemical burn triage.
  - **Severe Dehydration & Diarrhea:** Exact WHO standard 1-liter ORS reconstitution, age-based dosing, and sunken-fontanelle red flags.
  - **High Fever & Convulsions:** Cold sponging, recovery position, febrile convulsion hospital referral.
  - **Cuts, Bleeding & Animal Bites:** Direct pressure, rabies wound washing protocols.
  - **Fainting & Heat Stroke:** Elevation, shade cooling, airway management.
  - **Choking:** Heimlich maneuver and infant back-blow protocols.

### 7. Monthly Service Reminders
- 4-tier due date classification algorithm (Critical Overdue $>14\text{ days}$, Overdue $1\text{–}14\text{ days}$, Due Today, Upcoming $\le 7\text{ days}$).
- Tracks ANC check-ups, infant immunization milestones (BCG, Pentavalent, MR), and monthly NCD refill schedules.

---

## 4. Verified Technology Stack

| Layer | Component | Version / Specification | Rationale & Justification |
|:---|:---|:---|:---|
| **Runtime & Server** | Python / FastAPI / Uvicorn | Python 3.10+, FastAPI 0.115+, Uvicorn 0.32+ | Ultra-fast ASGI local web server with zero external database dependencies. |
| **Local Database** | SQLite 3 | Embedded (WAL Journal Mode, Foreign Keys ON) | Zero-maintenance ACID relational database ensuring no data loss on sudden power failure. |
| **Frontend Framework** | React 19 / TypeScript | React 19.0.0, TypeScript 5.7+ | Strict type safety, predictable UI state transitions, and responsive mobile rendering. |
| **Build & Styling** | Vite / Tailwind CSS | Vite 6.4+, Tailwind CSS 3.4+ | Instant sub-second HMR, optimized production bundle (792 kB minified). |
| **Icons & UI** | Lucide React | Lucide React 1.16+ | Clean, accessible clinical iconography with low bundle footprint. |
| **Search Engine** | BM25Okapi (In-Memory) | Custom zero-dependency Python & TypeScript implementations | Sub-millisecond vectorless search; runs on low-end 2GB RAM phones without embedding model overhead. |
| **Voice Interface** | Web Speech API | Native Browser SpeechRecognition & SpeechSynthesis | Zero-bandwidth offline speech recognition when device language packs are installed. |
| **Quality & Benchmarking** | Pytest / Custom Benchmarks | Pytest 9.1+, `eval/evaluate.py` | 80 automated unit/integration tests and 342-query clinical safety benchmark. |

---

## 5. Prerequisites

Before running the application, ensure your environment meets the following requirements:
- **Operating System:** Windows 10/11, Linux (Ubuntu 20.04+), or macOS (12+).
- **Python:** Version **3.10** or higher (tested on Python 3.10 through 3.14).
- **Node.js:** Version **18.0.0** or higher (tested on Node v20 and v26 with npm 10+).
- **Web Browser:** Modern Chromium-based browser (Google Chrome, Microsoft Edge, Brave) with JavaScript and LocalStorage enabled.

---

## 6. Installation Instructions

### 1. Clone the Repository
```bash
git clone https://github.com/your-org/syncpulse.git
cd syncpulse
```

### 2. Set Up Python Virtual Environment
```powershell
# Windows PowerShell:
python -m venv .venv
.venv\Scripts\Activate.ps1

# Linux / macOS:
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Python Dependencies
```bash
pip install -r requirements.txt
```

### 4. Install Frontend Dependencies & Build Bundle
```bash
cd web
npm install
npm run build
cd ..
```

---

## 7. Exact Startup Command

To launch the complete integrated application (serving both the backend API and the pre-built web frontend at a single local address):

```powershell
# From the project root:
.venv\Scripts\python -m uvicorn server.main:app --host 127.0.0.1 --port 8000
```

Once started, open your web browser and navigate to:
```
http://127.0.0.1:8000/
```

*(Optional Development Mode):* If actively modifying the React frontend source code, run `npm --prefix web run dev` in a separate terminal to enable Vite Hot Module Replacement on port `5173`.

---

## 8. Model Setup & Local Asset Footprint

SyncPulse was engineered to adhere to strict hardware limitations of entry-level Indian government smartphones (typically 2GB RAM, 32GB eMMC storage).

### Measured Resource Footprint (Audit Verified)
Run `python bench/measure_qa_performance.py` to inspect the exact asset profile:
- **Total Asset Footprint on Disk:** **1.58 MB** ($1,652,286\text{ bytes}$).
  - `data/protocols/` (Text Guidelines): 176.4 KB across 58 chunked clinical files.
  - `data/synthetic_register/households.json`: 183.1 KB (500 detailed household records).
  - SQLite Database (`register.db`): 495.6 KB fully indexed.
  - Evaluation Benchmarks (`escalation_set.jsonl`): 800.7 KB (342 clinical cases).
- **Subsystem Cold-Start Latency:** **4.48 milliseconds**.
- **Stage 1 Emergency Safety Gate Latency:** **0.89 milliseconds**.
- **Stage 3 & 4 Search Inference Latency:** **3.25 milliseconds** (P50: 0.67 ms).
- **Model Execution Memory Overhead:** **131.86 KB** (Active Process Peak RSS: ~21.6 MB).

### Extractive Adapter vs. Heavy LLMs
SyncPulse deliberately avoids deploying 4 GB–8 GB quantized LLMs (e.g., Llama-3 or Mistral) on field devices. On 2GB RAM phones, heavy LLMs cause out-of-memory crashes, deplete device batteries within 2 hours, and risk generating hallucinated medical dosages. 

Instead, SyncPulse's **Extractive Protocol Adapter** combines BM25Okapi keyword weighting with deterministic sentence extraction and exact substring verification. It guarantees that **100% of generated advice is verbatim grounded** in MoHFW protocols, while executing in single-digit milliseconds.

---

## 9. Offline Operation Instructions

SyncPulse is architected from the ground up for continuous offline operation:
1. **Initial Asset Bundling:** All application scripts, styles, icons, and clinical guidelines are packaged into static client bundles cached via Service Workers.
2. **Local Data Isolation:** All clinical records, visits, follow-up tasks, and emergency events are persisted in browser LocalStorage and the local SQLite database.
3. **Verification of Zero Network Dependence:**
   - Disconnect your computer or device completely from Wi-Fi and Ethernet (or enable Airplane Mode).
   - Refresh the page at `http://127.0.0.1:8000/`.
   - The green `⚡ 100% Offline Mode` banner will confirm full offline readiness.
   - You can search protocols, log patient visits, calculate Haversine distances, view First Aid protocols, and raise emergency escalations without a single dropped packet.
4. **Offline Export / Backup:** Frontline supervisors can export an encrypted JSON snapshot of the local database at any time by clicking **"Download Offline JSON Backup"** in the **System Status** screen.

---

## 10. Dataset Import & Reset Instructions

The application includes an idempotent, schema-validated database importer.

### Resetting to Pristine Demonstration State
To reset the local SQLite database and restore the original 500 synthetic households without modifying source files:

```powershell
python bench/reset_demo_data.py
```

**Output:**
```
============================================================
  SYNCPULSE DEMONSTRATION RESET COMPLETE
============================================================
Database File      : .../data/register.db
Source Register    : .../data/synthetic_register/households.json
Imported Households: 500 / 500
Rejected / Errors  : 0
Zero source records were modified or corrupted.
============================================================
```

### Resetting Client Browser Storage
In the web interface, navigate to the **System Status** screen and click **"Reset Demo State"**. This clears test visit logs and outbox queues in browser storage and reloads baseline records.

---

## 11. Verification & Benchmark Evaluation Results

All safety and performance claims are backed by automated evaluation scripts:

### 1. Emergency Escalation Safety Gate (Hard Gate)
```powershell
python eval/evaluate.py
```
**Verified Results:**
- **Evaluated Test Items:** 342 queries (232 Emergency, 110 Routine).
- **True Positives (TP):** 232 / 232.
- **False Negatives (FN):** **0** (Zero missed emergencies).
- **False Escalation Rate:** **0.0%** (Zero false alarms on routine queries).
- **Recall Target:** **100.0%** (Achieved 100.0%).
- **Evaluation Latency:** Average 0.138 ms per query.

### 2. End-to-End Pipeline & Retrieval Quality
```powershell
python eval/evaluate_pipeline.py
```
**Verified Results:**
- **Overall Decision Accuracy:** **100.0%** (96/96 development queries correct).
- **Hit@3 Protocol Retrieval:** **98.28%** (57/58 in-scope queries).
- **Paramedical Scope Refusal:** **100.0%** (15/15 unauthorized drug requests blocked).

### 3. Automated Test Suite
```powershell
pytest
```
**Verified Results:**
- **80 passed** across 11 test modules in **2.50 seconds** (Covering SQLite transactions, data validation, emergency gates, Haversine math, visit workflows, and offline recovery).

---

## 12. Known Limitations & Honest Disclosures

To ensure scientific integrity during hackathon judging, the following limitations are documented:
1. **Emergency Telephony:** SyncPulse cannot directly initiate automated cellular voice calls to `108` from a web browser without cellular hardware and user confirmation. The UI provides a one-click `tel:108` native dialer link.
2. **Offline Web Speech API:** Voice-to-text recognition in desktop Chromium browsers relies on the operating system's local speech engine. If offline language packs for Telugu or Hindi are not installed on the host OS, voice transcription may require connectivity or fallback to text.
3. **Straight-Line vs. Road Distance:** Map distance is computed using the Haversine formula on Earth's mean radius ($6371\text{ km}$). Because rural road layouts and monsoon terrain cannot be reliably modeled offline without gigabytes of routing graph data, the UI explicitly labels distances as *"Straight-line distance (Haversine formula)"*.
4. **Central Hub Synchronization:** The optional sync endpoint (`/api/sync`) requires network connectivity to reach a central health server. When operating disconnected, events remain safely queued in the local outbox.

---

## 13. Optional Central Backend Configuration

SyncPulse functions autonomously as a standalone offline node. However, when an ASHA worker reaches a Primary Health Centre with Wi-Fi, the system can sync with a central hub:
- **Sync Ingestion Endpoint:** `POST /api/sync` accepts JSON payloads containing batches of offline-recorded visits and emergency logs, reconciling outbox UUIDs.
- **Backup Snapshot Endpoint:** `GET /api/backup` generates an audit report of stored households, completed visits, and pending sync counts.
- **Host & Port Configuration:** Configurable via standard Uvicorn environment variables:
  ```powershell
  $env:PORT = "8080"
  uvicorn server.main:app --port 8080
  ```

---

## 14. Troubleshooting Steps

| Issue | Cause | Solution |
|:---|:---|:---|
| `Address already in use: 8000` | A previous instance of Uvicorn or another service is running on port 8000. | Stop the process with `Get-Process python \| Stop-Process -Force` in PowerShell, or choose an alternate port: `--port 8081`. |
| `[WinError 32] The process cannot access the file because it is being used by another process` | SQLite WAL database is locked by an active Python process during file deletion. | Run `python bench/reset_demo_data.py`. The script will automatically truncate existing tables within SQLite without requiring process termination. |
| Browser shows stale UI or cached errors | Aggressive Service Worker caching during active code edits. | Hard refresh the browser (`Ctrl + Shift + R`) or open DevTools > Application > Storage and click **"Clear site data"**. |
| Microphone button does not transcribe speech | Microphone permission denied, or offline speech pack missing in browser. | Allow microphone permissions in browser settings. For live testing, click any of the 4 pre-configured symptom chips below the search bar. |

---

## 15. Demonstration Plan Summary

For a guided, 10-step click-by-click evaluation walkthrough designed for hackathon judges, refer to the complete demonstration plan:
👉 **[Read the Full 10-Step Hackathon Demonstration Plan (`docs/DEMO_PLAN.md`)](file:///c:/Users/gaura/Downloads/syncpluse/docs/DEMO_PLAN.md)**

*SyncPulse — Built with clinical safety, explainable AI, and zero compromise for the frontline workers protecting rural India.*
