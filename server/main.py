"""
FastAPI application server for SyncPulse — Offline-First ASHA Healthcare Platform.

Serves:
- /api/ask: Complete 4-stage offline clinical pipeline
- /api/households: Search & filter the 500-family register
- /api/households/{id}: Individual & household profile, history, follow-ups
- /api/households/{id}/phone: Edit permitted contact phone
- /api/visits: Prioritised daily visit list from SQLite
- /api/visits/{id}/record: Record clinical visit outcome with vitals & follow-up
- /api/visits/{id}/done: Mark visit as completed (legacy compatibility)
- /api/follow_ups: Get & complete follow-up tasks
- /api/patients: Patient account records and search
- /api/alerts: Emergency messages, triage, and 108 referral
- /api/import: Repeatable register importer with validation report
- /api/first_aid: Approved first-aid guides
- /api/health_topics: Health knowledge hub articles
- /api/sync: Idempotent batch offline queue sync
- /api/status: System health, pack version, and statistics
- Mounts web/dist for single-command PWA serving
"""

from __future__ import annotations

import json
import os
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from core.db import get_db
from core.importer import ImportReport, RegisterImporter
from core.pipeline import FrontlineCompanionPipeline, PipelineResponse
from core.reminders import FollowUpGap, MonthlyReminder, ReminderService
from core.repository import SyncPulseRepository
from core.visits import VisitItem, VisitManager

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SYNCPULSE_DATA_DIR = PROJECT_ROOT / "data" / "syncpulse"

# Initialize core services & data repositories
pipeline = FrontlineCompanionPipeline()
visit_mgr = VisitManager()
repo = SyncPulseRepository()
importer = RegisterImporter()

# Pre-seed SQLite database from 500-family register if empty
try:
    reg_file = PROJECT_ROOT / "data" / "synthetic_register" / "households.json"
    if reg_file.exists():
        importer.import_from_file(reg_file)
except Exception as e:
    print(f"Warning: Initial register import note: {e}")

app = FastAPI(
    title="SyncPulse — Offline-First ASHA Healthcare Platform",
    version="2.0.0",
    description="Healthcare Connected. Even Offline. ASHA decision support, household register & emergency triage.",
)

# Enable CORS for local PWA dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request & Response schemas
class AskRequest(BaseModel):
    query: str = Field(default="", min_length=0, description="Clinical query from frontline worker")


class MarkDoneRequest(BaseModel):
    notes: Optional[str] = Field(default="", description="Observations / clinical notes from visit")


class RecordVisitRequest(BaseModel):
    service_rendered: str = Field(..., description="Service provided from protocol")
    visit_outcome: str = Field(..., description="Clinical observation outcome")
    vitals: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None
    follow_up_task: Optional[str] = None
    follow_up_due_date: Optional[str] = None
    follow_up_priority: Optional[str] = "ROUTINE"
    asha_id: Optional[str] = "ASHA-8841"


class UpdatePhoneRequest(BaseModel):
    phone: str = Field(..., min_length=10, max_length=10, description="10-digit mobile number")


class UpdateLocationRequest(BaseModel):
    latitude: float = Field(..., ge=-90.0, le=90.0, description="Latitude in decimal degrees (-90 to +90)")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="Longitude in decimal degrees (-180 to +180)")
    accuracy_m: Optional[float] = Field(default=None, description="GPS sensor accuracy in meters if available")
    source: Optional[str] = Field(default="MANUAL_ENTRY", description="'GPS_CAPTURE' or 'MANUAL_ENTRY'")


class CompleteFollowUpRequest(BaseModel):
    completion_notes: Optional[str] = ""


class PatientModel(BaseModel):
    patient_id: str
    name: str
    age: int
    gender: str
    village: str
    contact_phone: str
    family_head: str
    blood_group: Optional[str] = "Unknown"
    is_pregnant: Optional[bool] = False
    gestational_weeks: Optional[int] = None
    edd: Optional[str] = None
    is_high_risk: Optional[bool] = False
    risk_condition: Optional[str] = None
    allergies: Optional[List[str]] = []
    current_medications: Optional[List[str]] = []
    assigned_asha: Optional[str] = "ASHA-8841"
    last_visit_date: Optional[str] = None
    next_visit_date: Optional[str] = None
    visit_history: Optional[List[Dict[str, Any]]] = []
    reminders: Optional[List[Dict[str, Any]]] = []


class EmergencyAlertModel(BaseModel):
    alert_id: str
    patient_id: str
    patient_name: str
    village: str
    contact_phone: str
    timestamp: str
    severity: str
    symptoms: str
    description: str
    location: Optional[str] = "Village Home"
    delivery_status: Optional[str] = "DELIVERED"
    is_acknowledged: Optional[bool] = False


class SyncAction(BaseModel):
    client_uuid: str
    action_type: str
    household_id: Optional[str] = None
    timestamp: str
    notes: Optional[str] = ""
    payload: Optional[Dict[str, Any]] = None


class SyncRequest(BaseModel):
    items: Optional[List[Dict[str, Any]]] = None
    actions: Optional[List[SyncAction]] = None


# Helper data loaders
def _load_json(filename: str) -> List[Dict[str, Any]]:
    p = SYNCPULSE_DATA_DIR / filename
    if p.exists():
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def _save_json(filename: str, data: Any):
    p = SYNCPULSE_DATA_DIR / filename
    with open(p, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


# ==============================================================================
# API Routes
# ==============================================================================

@app.post("/api/ask", response_model=Dict[str, Any])
def api_ask(req: AskRequest):
    """
    Evaluates clinical query through the 4-stage offline pipeline:
    Escalation -> Scope Refusal -> BM25 Retrieval -> Extractive Grounded Answer.
    """
    resp: PipelineResponse = pipeline.process_query(req.query)
    return resp.to_dict()


# --- HOUSEHOLDS & REGISTER ---

@app.get("/api/households", response_model=Dict[str, Any])
def api_search_households(
    q: Optional[str] = None,
    village: Optional[str] = None,
    beneficiary_type: Optional[str] = None,
    is_high_risk: Optional[bool] = None,
    visited_status: Optional[str] = None,
    limit: int = Query(default=50, le=100),
    offset: int = 0,
):
    """
    Search and filter the 500-family register from SQLite.
    """
    results, total_count = repo.search_households(
        query_str=q,
        village=village,
        beneficiary_type=beneficiary_type,
        is_high_risk=is_high_risk,
        visited_status=visited_status,
        limit=limit,
        offset=offset,
    )
    return {
        "total": total_count,
        "limit": limit,
        "offset": offset,
        "households": results,
    }


@app.get("/api/households/{household_id}", response_model=Dict[str, Any])
def api_get_household(household_id: str):
    """
    Returns single household profile, individual beneficiaries, visit history, and follow-ups.
    """
    hh = repo.get_household(household_id)
    if not hh:
        raise HTTPException(status_code=404, detail="Household record not found")
    return hh


@app.put("/api/households/{household_id}/phone", response_model=Dict[str, Any])
def api_update_household_phone(household_id: str, req: UpdatePhoneRequest):
    """
    Updates the contact phone for a household (permitted field).
    """
    updated = repo.update_household_phone(household_id, req.phone)
    if not updated:
        raise HTTPException(status_code=404, detail="Household record not found")
    return {"status": "success", "household_id": household_id, "phone": req.phone}


@app.put("/api/households/{household_id}/location", response_model=Dict[str, Any])
def api_update_household_location(household_id: str, req: UpdateLocationRequest):
    """
    Saves verified or manually entered coordinates for a household.
    Does NOT invent coordinates.
    """
    success = repo.update_household_location(
        household_id=household_id,
        latitude=req.latitude,
        longitude=req.longitude,
        accuracy_m=req.accuracy_m,
        source=req.source or "MANUAL_ENTRY",
    )
    if not success:
        raise HTTPException(status_code=404, detail="Household record not found")
    return {
        "status": "success",
        "household_id": household_id,
        "latitude": req.latitude,
        "longitude": req.longitude,
        "source": req.source,
    }


# --- VISITS & CLINICAL WORKFLOW ---

@app.get("/api/visits", response_model=Dict[str, Any])
def api_get_visits(
    as_of_date: Optional[str] = None,
    village: Optional[str] = None,
    limit: int = 50,
    include_completed: bool = False,
    worker_lat: Optional[float] = None,
    worker_lon: Optional[float] = None,
    filter_tab: str = "all",
):
    """
    Returns prioritized daily visit list from SQLite using 4-tier clinical triage.
    Clinical urgency strictly dominates distance. Straight-line distance via Haversine
    serves as a secondary convenience tie-breaker within the same clinical priority.
    """
    ref_d = date.fromisoformat(as_of_date) if as_of_date else date(2026, 10, 20)
    items: List[VisitItem] = visit_mgr.get_visit_list(
        as_of_date=ref_d,
        village=village,
        limit=limit,
        include_completed=include_completed,
        worker_lat=worker_lat,
        worker_lon=worker_lon,
        filter_tab=filter_tab,
    )
    return {
        "as_of_date": ref_d.isoformat(),
        "total_returned": len(items),
        "worker_location": (
            {"latitude": worker_lat, "longitude": worker_lon}
            if worker_lat is not None and worker_lon is not None
            else None
        ),
        "filter_tab": filter_tab,
        "visits": [item.to_dict() for item in items],
    }


@app.get("/api/reminders", response_model=Dict[str, Any])
def api_get_reminders(as_of_date: Optional[str] = None):
    """
    Generates monthly visit reminders from approved MoHFW schedules and actual due dates,
    and detects overdue recorded follow-up tasks from real records.
    Explicitly labeled as on-device local storage (zero fabricated push delivery).
    """
    ref_date_str = as_of_date or "2026-10-20"
    reminder_svc = ReminderService()
    reminders = reminder_svc.generate_monthly_reminders(ref_date_str)
    gaps = reminder_svc.detect_follow_up_gaps(ref_date_str)
    return {
        "as_of_date": ref_date_str,
        "total_reminders": len(reminders),
        "total_gaps": len(gaps),
        "reminders": [r.to_dict() for r in reminders],
        "follow_up_gaps": [g.to_dict() for g in gaps],
        "notification_channel": "LOCAL_DEVICE_ONLY",
    }


@app.post("/api/follow_ups/{follow_up_id}/complete", response_model=Dict[str, Any])
def api_complete_follow_up(follow_up_id: str, req: CompleteFollowUpRequest):
    """
    Marks an overdue or pending follow-up task as completed with completion notes.
    """
    success = repo.complete_follow_up(follow_up_id, req.completion_notes or "")
    if not success:
        raise HTTPException(status_code=404, detail="Follow-up task not found")
    return {"status": "success", "follow_up_id": follow_up_id, "status_value": "COMPLETED"}


@app.post("/api/visits/{household_id}/record", response_model=Dict[str, Any])
def api_record_visit(household_id: str, req: RecordVisitRequest):
    """
    Records a clinical visit outcome, captures vitals, creates follow-up task,
    and updates SQLite atomically.
    """
    try:
        res = repo.record_visit_outcome(
            household_id=household_id,
            service_rendered=req.service_rendered,
            visit_outcome=req.visit_outcome,
            vitals=req.vitals,
            notes=req.notes,
            follow_up_task=req.follow_up_task,
            follow_up_due_date=req.follow_up_due_date,
            follow_up_priority=req.follow_up_priority or "ROUTINE",
            asha_id=req.asha_id or "ASHA-8841",
        )
        return res
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/visits/{household_id}/done", response_model=Dict[str, Any])
def api_mark_visit_done(household_id: str, req: MarkDoneRequest):
    """
    Legacy visit completion endpoint for backwards compatibility.
    """
    ok = visit_mgr.mark_visited(household_id, notes=req.notes or "")
    if not ok:
        raise HTTPException(status_code=400, detail="Failed to mark visit completed")
    return {"status": "success", "household_id": household_id, "timestamp": datetime.now(timezone.utc).isoformat()}


# --- FOLLOW-UP TASKS ---

@app.get("/api/follow_ups", response_model=List[Dict[str, Any]])
def api_get_follow_ups(household_id: Optional[str] = None, status: Optional[str] = None):
    """
    Returns pending and completed follow-up tasks.
    """
    return repo.get_follow_ups(household_id=household_id, status=status)


@app.post("/api/follow_ups/{follow_up_id}/complete", response_model=Dict[str, Any])
def api_complete_follow_up(follow_up_id: str, req: CompleteFollowUpRequest):
    """
    Marks a follow-up task completed.
    """
    ok = repo.complete_follow_up(follow_up_id, req.completion_notes or "")
    if not ok:
        raise HTTPException(status_code=404, detail="Follow-up task not found")
    return {"status": "success", "follow_up_id": follow_up_id}


# --- PATIENTS (SUPPLEMENTAL EXTENDED PROFILES) ---

@app.get("/api/patients", response_model=List[Dict[str, Any]])
def api_get_patients(village: Optional[str] = None, search: Optional[str] = None):
    patients = _load_json("patients.json")
    if village and village != "All Villages":
        patients = [p for p in patients if p.get("village") == village]
    if search:
        s = search.lower()
        patients = [
            p for p in patients
            if s in p.get("name", "").lower() or s in p.get("patient_id", "").lower()
        ]
    return patients


@app.get("/api/patients/{patient_id}", response_model=Dict[str, Any])
def api_get_patient(patient_id: str):
    patients = _load_json("patients.json")
    for p in patients:
        if p.get("patient_id", "").lower() == patient_id.lower():
            return p
    raise HTTPException(status_code=404, detail="Patient not found")


@app.post("/api/patients", response_model=Dict[str, Any])
def api_register_patient(patient: PatientModel):
    patients = _load_json("patients.json")
    patients.insert(0, patient.model_dump())
    _save_json("patients.json", patients)
    return {"status": "success", "patient_id": patient.patient_id}


# --- EMERGENCY ALERTS ---

@app.get("/api/alerts", response_model=List[Dict[str, Any]])
def api_get_alerts(severity: Optional[str] = None):
    alerts = _load_json("emergency_alerts.json")
    if severity and severity != "ALL":
        alerts = [a for a in alerts if a.get("severity") == severity]
    return alerts


@app.post("/api/alerts", response_model=Dict[str, Any])
def api_create_alert(alert: EmergencyAlertModel):
    alerts = _load_json("emergency_alerts.json")
    alerts.insert(0, alert.model_dump())
    _save_json("emergency_alerts.json", alerts)

    # Also log to SQLite emergency_events
    repo.record_emergency_event(alert.model_dump())
    return {"status": "success", "alert_id": alert.alert_id}


# --- PROTOCOL CONTENT ---

@app.get("/api/first_aid", response_model=List[Dict[str, Any]])
def api_get_first_aid():
    return _load_json("first_aid.json")


@app.get("/api/health_topics", response_model=List[Dict[str, Any]])
def api_get_health_topics():
    return _load_json("health_topics.json")


# --- DATA IMPORTER ---

@app.post("/api/import", response_model=Dict[str, Any])
def api_import_register(records: List[Dict[str, Any]]):
    """
    Repeatable register importer: validates records, prevents duplicates,
    preserves user visits, and returns an ImportReport.
    """
    report: ImportReport = importer.import_records(records)
    return report.to_dict()


# --- SYNC & STATUS ---

@app.post("/api/sync", response_model=Dict[str, Any])
def api_sync_queue(req: SyncRequest):
    """
    Idempotent batch sync for offline outbox actions collected in client IndexedDB.
    """
    action_items = req.items or (
        [
            {"client_uuid": a.client_uuid, "action_type": a.action_type, "household_id": a.household_id, "notes": a.notes, "payload": a.payload}
            for a in req.actions
        ]
        if req.actions else []
    )

    synced_count = 0
    for item in action_items:
        action_type = item.get("action_type") or item.get("action")
        entity_type = item.get("entity_type")

        if action_type in ("MARK_VISITED", "complete") or entity_type == "visit":
            hid = item.get("household_id") or (item.get("payload", {}).get("household_id"))
            if hid:
                notes = item.get("notes") or (item.get("payload", {}).get("visit_notes", ""))
                visit_mgr.mark_visited(hid, notes=notes)
                synced_count += 1
        elif action_type in ("REGISTER_PATIENT", "create") and entity_type == "patient":
            payload = item.get("payload")
            if payload:
                patients = _load_json("patients.json")
                if not any(p["patient_id"] == payload.get("patient_id") for p in patients):
                    patients.insert(0, payload)
                    _save_json("patients.json", patients)
                synced_count += 1
        elif action_type in ("RAISE_ALERT", "create", "update") and entity_type == "emergency_alert":
            payload = item.get("payload")
            if payload:
                # Mark as synced to hub
                payload_copy = dict(payload)
                payload_copy["delivery_status"] = "SENT_SUCCESSFULLY"
                payload_copy["status_explanation"] = "Successfully synchronized with sub-center SQLite register."
                alerts = _load_json("emergency_alerts.json")
                if not any(a["alert_id"] == payload_copy.get("alert_id") for a in alerts):
                    alerts.insert(0, payload_copy)
                else:
                    for i, a in enumerate(alerts):
                        if a["alert_id"] == payload_copy.get("alert_id"):
                            alerts[i] = {**a, **payload_copy}
                _save_json("emergency_alerts.json", alerts)
                repo.record_emergency_event(payload_copy)
                synced_count += 1

    return {
        "status": "success",
        "processed_actions": len(action_items),
        "synced_count": synced_count,
        "server_time": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/api/backup", response_model=Dict[str, Any])
def api_get_backup():
    """
    Returns a safe export summary of the local SQLite register, visits, follow-ups, and alerts.
    Operates entirely offline on the local node.
    """
    with repo.db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) AS total FROM households")
        hh_count = cursor.fetchone()["total"]

        cursor.execute("SELECT COUNT(*) AS total FROM visit_outcomes")
        visits_count = cursor.fetchone()["total"]

        cursor.execute("SELECT COUNT(*) AS total FROM follow_ups")
        follow_up_count = cursor.fetchone()["total"]

        cursor.execute("SELECT COUNT(*) AS total FROM emergency_events")
        alerts_count = cursor.fetchone()["total"]

        cursor.execute("SELECT COUNT(*) AS total FROM sync_outbox WHERE status = 'PENDING'")
        pending_outbox = cursor.fetchone()["total"]

    return {
        "app_name": "SyncPulse",
        "pack_version": "2.0.0",
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "storage_engine": "SQLite WAL Mode (Local On-Device)",
        "stats": {
            "households": hh_count,
            "recorded_visits": visits_count,
            "follow_ups": follow_up_count,
            "emergency_events": alerts_count,
            "pending_sync_outbox": pending_outbox,
        },
        "privacy_notice": "Stored locally without external analytics or telemetry.",
    }


@app.get("/api/status", response_model=Dict[str, Any])
def api_status():
    """
    Health check and dashboard status metrics.
    """
    stats = visit_mgr.get_summary_stats()
    return {
        "status": "online",
        "app_name": "SyncPulse",
        "tagline": "Healthcare Connected. Even Offline.",
        "pack_version": "2.0.0",
        "pack_name": "SYNCPULSE_ASHA_HEALTHCARE_PLATFORM_AP_2026",
        "offline_ready": True,
        "execution_mode": "Deterministic Rules + BM25 Extractive (Zero-Model CPU)",
        "stats": stats,
    }


# Mount Static PWA assets from web/dist
dist_dir = PROJECT_ROOT / "web" / "dist"
if dist_dir.exists():
    app.mount("/", StaticFiles(directory=dist_dir, html=True), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server.main:app", host="127.0.0.1", port=8000, reload=False)
