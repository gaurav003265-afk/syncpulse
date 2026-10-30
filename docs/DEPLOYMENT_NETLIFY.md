# SyncPulse Deployment & Netlify Hosting Guide

## 1. Quick Netlify Deployment (Zero-Node Production Hosting)

SyncPulse is pre-built as a progressive web application inside `web/dist` with a self-contained offline clinical reasoning engine, IndexedDB persistence, and local knowledge pack. It requires **zero Node.js or Python runtime** on Netlify's edge servers.

### Option A: Netlify CLI (Fastest)
From the project root:
```bash
# 1. Install Netlify CLI if not present
npm install -g netlify-cli

# 2. Deploy directly from pre-built dist
netlify deploy --dir=web/dist --prod
```

### Option B: Netlify Web Dashboard (Drag-and-Drop or Git)
1. Log into your [Netlify Dashboard](https://app.netlify.com).
2. Go to **Sites** $\to$ drag and drop the `web/dist` folder directly onto the upload zone.
3. Alternatively, connect this Git repository and configure:
   - **Publish directory:** `web/dist`
   - **Build command:** *(leave empty, pre-built)*

---

## 2. Environment Variables Documentation

For full multi-user production synchronization, configure the following environment variables in Netlify or your local `.env`:

| Variable Name | Default / Demo Value | Production Purpose |
|---|---|---|
| `VITE_API_BASE_URL` | `http://localhost:8000` | URL of the central health post FastAPI / Serverless backend. |
| `SYNCPULSE_ENV` | `production` | Sets environment mode (`development`, `staging`, `production`). |
| `ASHA_DISTRICT_CODE` | `AP-KRI` | District administrative identifier (e.g., Krishna, AP). |
| `OFFLINE_SYNC_INTERVAL_SEC` | `300` | Automatic background sync retry interval in seconds when online. |
| `ENABLE_AMBULANCE_DISPATCH_API` | `false` | Enables direct automated webhook trigger to 108 emergency service dispatch. |

---

## 3. Production Backend Integrations Still Required

Before deploying to live clinical operations with real patient identities:

1. **National RCH Portal Integration:**
   - Connect the sync queue adapter to push completed ANC visits and child immunizations to the central Reproductive and Child Health (RCH) portal via FHIR/ABDM APIs.
2. **Ayushman Bharat Digital Mission (ABDM) ABHA ID:**
   - Integrate ABHA (Ayushman Bharat Health Account) creation and verification for patients.
3. **Emergency SMS / IVR Gateway:**
   - In areas where 2G data fails but basic GSM telephony works, configure an SMS outbox fallback that sends emergency codes (`ALT-P101-CRIT-HEMORRHAGE`) directly to the PHC Medical Officer's phone.
4. **End-to-End Encryption (E2EE):**
   - Apply AES-GCM-256 client-side encryption for patient records stored on worker phones, with biometric or PIN-derived keys.
