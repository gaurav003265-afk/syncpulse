# SyncPulse (Sakhi FieldOS) — Live Hackathon Demonstration Plan

**Target Audience:** Hackathon Judges, Clinical Evaluators, Public Health Technologists  
**Duration:** 7–10 Minutes  
**Demonstration Mode:** 100% Offline Capable (No Internet Required)  
**Standard Demo State:** Reset via `python bench/reset_demo_data.py` or UI **"Reset Demo State"** button in System Status.

---

## Demonstration Overview & Core Value Proposition

SyncPulse is an offline-first frontline healthcare operating system designed for ASHA (Accredited Social Health Activist) workers in rural India.

During this demonstration, judges will observe:
1. **Zero-Latency Offline Execution:** Sub-millisecond clinical safety triage and search running purely on-device (1.58 MB total asset footprint).
2. **100% Recall Emergency Gate:** Instant, deterministic escalation for life-threatening obstetric and pediatric red flags before any AI or search can hallucinate.
3. **Explainable Protocol Citations:** Every guidance item is strictly grounded in official MoHFW / WHO guidelines with document, chapter, and page citations.
4. **Paramedical Scope Protection:** Deterministic refusal when asked to prescribe scheduled antibiotics or medications beyond an ASHA worker's legal scope.
5. **Real Local Data Layer:** 500-household synthetic register in SQLite WAL, real visit recording, and Haversine straight-line distance.

---

## What NOT to Demonstrate (Honest Transparency)

To maintain complete credibility with technical and medical judges, **do NOT** claim or demonstrate:
1. **Direct Cellular Phone Calls from Web:** Do NOT claim the browser initiates automated cellular calls to 108. The system displays a direct emergency dialer button (`tel:108`) that opens the mobile phone's native dialer.
2. **Automated SMS Delivery while Offline:** Do NOT claim offline emergency alerts reach doctors via SMS while disconnected. SyncPulse transparently labels alerts as:  
   `Saved Locally (On-Device Only) • Notification Service Not Configured`.
3. **Turn-by-Turn Road Routing:** Do NOT claim the map calculates turn-by-turn road times. SyncPulse strictly labels distance as `Approximate straight-line distance (Haversine formula)`.
4. **Heavy Multi-Billion LLMs running on Device:** Do NOT claim a 7B LLM is running inside the browser. SyncPulse uses a deterministic BM25 vectorless search and zero-shot extractive adapter specifically optimized for low-end 2GB RAM phones.

---

## 10-Step Step-by-Step Live Demonstration Sequence

| Step | Screen / Module | Action / Test Input | Expected System Output | Key Clinical / Technical Value |
|:---:|:---|:---|:---|:---|
| **1** | **System Status** | Open `System Status` tab. Click **"Reset Demo State"** | Shows 500 households loaded, 58 protocol chunks indexed, Emergency Gate Active (100% Recall), Connectivity indicator showing `⚡ 100% Offline Mode`. | Proves clean repeatable baseline without corrupted test data. |
| **2** | **Dashboard** | View Home Dashboard KPI cards | Shows **Today's Due Visits (8)**, **High-Risk Beneficiaries (76)**, **Overdue Visits (32)**, and **Locally Queued Events (0)**. | Metrics calculated dynamically from local SQLite database, not hardcoded mocks. |
| **3** | **Ask Sakhi (Emergency)** | Type or Speak:  <br>`"Woman 7 months pregnant has heavy bleeding and severe headache"` | **Instant Red Emergency Alert Card (Stage 1 Hard Gate)**: <br>• Triage: `CRITICAL OBSTETRIC EMERGENCY`<br>• Action: `Immediate 108 Emergency Ambulance Dispatch`<br>• Protocol: `MoHFW Maternal Health Protocols (Section 4.2)`<br>• Zero model latency ($< 1\text{ ms}$). Auto-logs to Emergency Desk. | Demonstrates **100% Recall Hard Safety Gate**. Bypasses search and LLM to prevent dangerous delays or hallucinations. |
| **4** | **Ask Sakhi (Routine Care)** | Type: <br>`"What is the schedule for routine ANC visits?"` | **Verified Protocol Guidance Card**: <br>• Recommended: 4 ANC visits (Registration $\le 12$ wks, 14–26 wks, 28–34 wks, 36 wks–term).<br>• Citation: `MoHFW Maternal Health Protocols (Page 12)`.<br>• Confidence: `High (Protocol Grounded)`. | Grounded clinical protocol retrieval with exact document and page citation. |
| **5** | **Ask Sakhi (Nuanced Referral)** | Type: <br>`"Child has mild cough for 3 days with no fast breathing and no chest indrawing"` | **Non-Emergency Referral & Monitoring Card**: <br>• Classification: `No Pneumonia — Home Care & Monitoring`<br>• Advice: Warm fluids, continue feeding, check respiratory rate.<br>• Red Flags to Watch: Fast breathing ($> 50$ breaths/min), chest indrawing, stridor.<br>• Citation: `IMNCI Guidelines (Section 3.1)`. | Proves nuanced clinical stratification: avoids unnecessary hospital panics while teaching danger signs. |
| **6** | **Ask Sakhi (Scope Refusal)** | Type: <br>`"What dose of Amoxicillin should I give to the child for fever?"` | **Safety Scope Refusal Warning Card**: <br>• Status: `REFUSED — Outside Frontline Health Worker Scope`<br>• Warning: Frontline ASHA workers cannot prescribe antibiotics.<br>• Approved Action: Refer to Primary Health Centre (PHC) Medical Officer for clinical examination and prescription. | Enforces legal and clinical boundaries; prevents improper antibiotic stewardship. |
| **7** | **The Cure Window (First Aid)** | Click **The Cure Window** on Dashboard. Select `Dehydration & ORS Solution`. | Step-by-step interactive first-aid guide: <br>• Preparation of standard 1-liter ORS.<br>• Correct dosage by age.<br>• Danger signs requiring immediate IV fluids (sunken eyes, lethargy, skin pinch $> 2$ sec). | Rapid accessible clinical guidance for life-saving field interventions without internet. |
| **8** | **Household Register & Proximity** | Navigate to `Household Register`. Filter by `High-Risk`. Select `HH-0012 (Kavitha Devi)`. | Displays patient profile, risk tag (`Severe Anemia`), due dates, and straight-line proximity radar (`240 meters away (Straight-line)`). | Real relational data model connecting households, individual patients, and GPS coordinates. |
| **9** | **Visit Outcome Recording** | On `Kavitha Devi` profile, click **"Record Visit Outcome"**. Fill BP (`130/85`), Hb (`8.2 g/dL`), Service (`IFA Tablets Distributed`). Click Save. | Success toast: `Visit outcome saved locally`. Profile updates visit timeline. Sync outbox queues update locally (`1 pending transmission`). | ACID SQLite transaction preserving field-recorded clinical observations offline. |
| **10** | **Emergency Desk & Audit Trail** | Navigate to `Emergency Desk`. | Displays the automated emergency alert from Step 3 alongside test emergency records. Shows delivery badge: `Saved Locally (On-Device Only) • Notification Service Not Configured`. | Honest, tamper-evident audit logging for rural emergency escalation without deceptive fake sync claims. |

---

## Common Live Demo Failure Modes & Rapid Recovery

| Potential Failure Mode | Root Cause | Immediate Recovery Action (Under 5 Seconds) |
|:---|:---|:---|
| **Browser shows white screen or stale scripts** | Aggressive browser caching during local development | Press `Ctrl + Shift + R` (Hard Reload) or clear Service Worker in DevTools > Application. |
| **Port 8000 already bound** | A previous Python background server process is running | Run `Get-Process python \| Stop-Process -Force` in PowerShell, then re-launch `python -m uvicorn server.main:app --port 8000`. |
| **Database shows dirty test records from practice** | Modified during previous trial runs | Click **"Reset Demo State"** on the System Status screen, or run `python bench/reset_demo_data.py`. Takes $< 1\text{ second}$. |
| **Microphone input produces no text in offline mode** | Web Speech API in desktop Chromium lacks local offline speech pack | Click the microphone icon to toggle off, and use the pre-tested text prompt buttons directly below the search bar. |
| **Geolocation displays "Distance unavailable"** | Browser geolocation permission dismissed or denied | Click "Enter Coordinates Manually" on household profile, or use existing pre-calibrated synthetic household coordinates. |

---

## Verifiable Benchmark Proofs to Show the Jury

When technical judges ask for architecture verification, point directly to these pre-compiled benchmarks:

```powershell
# 1. 100% Recall Emergency Gate Benchmark (342 queries, 0 FN)
python eval/evaluate.py

# 2. Complete End-to-End Test Suite (80 passing tests)
pytest

# 3. Microsecond Cold-Start & Asset Footprint Audit (1.58 MB total)
python bench/measure_qa_performance.py
```

*SyncPulse demonstrates that frontline AI can be safe, transparent, ultra-lightweight, and 100% offline-resilient.*
