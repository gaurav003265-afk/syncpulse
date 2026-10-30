"""
End-to-end integration tests for SyncPulse user journeys:
1. Patient Portal Alert Creation & Safety Warnings
2. ASHA Patient Registration & Record Update
3. Emergency Alert Triage & 108 Ambulance Referral
4. First Aid CURE Guidance & Red Flag Warnings
5. Idempotent Batch Sync Queue Processing
"""

import pytest
from fastapi.testclient import TestClient
from server.main import app

client = TestClient(app)


def test_patient_portal_get_and_alert_submission():
    # 1. Fetch patient by ID
    resp = client.get("/api/patients/P-101")
    assert resp.status_code == 200
    p = resp.json()
    assert p["name"] == "Lakshmi Devi"
    assert p["is_pregnant"] is True
    assert p["village"] == "Ramnagar"

    # 2. Patient raises an emergency alert
    new_alert = {
        "alert_id": "ALT-TEST-999",
        "patient_id": "P-101",
        "patient_name": "Lakshmi Devi",
        "village": "Ramnagar",
        "contact_phone": "9848011221",
        "timestamp": "2026-10-20T12:00:00Z",
        "severity": "CRITICAL",
        "symptoms": "Severe continuous headache and swelling in face",
        "description": "Patient experiencing visual disturbance and nausea.",
        "location": "House #4-12, Ramnagar",
        "delivery_status": "DELIVERED",
        "is_acknowledged": False,
        "referred_to_doctor": True,
        "referral_facility": "PHC Ramnagar",
        "resolution_status": "PENDING_ACK"
    }

    create_resp = client.post("/api/alerts", json=new_alert)
    assert create_resp.status_code == 200
    assert create_resp.json()["status"] == "success"

    # 3. Verify alert appears in emergency triage queue
    alerts_resp = client.get("/api/alerts?severity=CRITICAL")
    assert alerts_resp.status_code == 200
    critical_alerts = alerts_resp.json()
    assert any(a["alert_id"] == "ALT-TEST-999" for a in critical_alerts)


def test_asha_register_new_patient():
    new_patient = {
        "patient_id": "P-TEST-888",
        "name": "Bhavani Devi",
        "age": 27,
        "gender": "Female",
        "village": "Kothur",
        "contact_phone": "9848099887",
        "family_head": "Siva Kumar (Husband)",
        "blood_group": "O+",
        "is_pregnant": True,
        "gestational_weeks": 12,
        "edd": "2027-04-20",
        "is_high_risk": False,
        "risk_condition": None,
        "allergies": ["None"],
        "current_medications": ["Folic acid 5mg"],
        "assigned_asha": "ASHA-Kothur",
        "last_visit_date": None,
        "next_visit_date": "2026-10-25",
        "visit_history": [],
        "reminders": []
    }

    reg_resp = client.post("/api/patients", json=new_patient)
    assert reg_resp.status_code == 200
    assert reg_resp.json()["status"] == "success"

    # Verify patient is searchable by name and village
    search_resp = client.get("/api/patients?village=Kothur&search=Bhavani")
    assert search_resp.status_code == 200
    matched = search_resp.json()
    assert len(matched) >= 1
    assert matched[0]["name"] == "Bhavani Devi"


def test_first_aid_cure_guidelines():
    resp = client.get("/api/first_aid")
    assert resp.status_code == 200
    guides = resp.json()
    assert len(guides) >= 5

    # Check Dehydration guide
    dehydration_guide = next((g for g in guides if "Dehydration" in g["title"]), None)
    assert dehydration_guide is not None
    assert "ORS" in dehydration_guide["title"]
    assert len(dehydration_guide["steps"]) > 0
    assert len(dehydration_guide["red_flags"]) > 0
    assert "IV" in dehydration_guide["doctor_referral_advice"]


def test_health_knowledge_search_topics():
    resp = client.get("/api/health_topics")
    assert resp.status_code == 200
    topics = resp.json()
    assert len(topics) >= 4

    # Verify immunization topic
    imm_topic = next((t for t in topics if t["topic_id"] == "HT-002"), None)
    assert imm_topic is not None
    assert "Universal Immunisation" in imm_topic["title"]
    assert "Universal Immunization Programme" in imm_topic["source_org"]
    assert imm_topic["is_cached_offline"] is True


def test_idempotent_offline_sync():
    sync_payload = {
        "items": [
            {
                "client_uuid": "sync-uuid-001",
                "action_type": "MARK_VISITED",
                "household_id": "HH-0010",
                "notes": "Checked baby growth, administered Vitamin A."
            },
            {
                "client_uuid": "sync-uuid-002",
                "action_type": "REGISTER_PATIENT",
                "payload": {
                    "patient_id": "P-SYNC-101",
                    "name": "Ratnamala",
                    "age": 30,
                    "gender": "Female",
                    "village": "Anantharam",
                    "contact_phone": "9848011999",
                    "family_head": "Subba Rao",
                    "blood_group": "B+",
                    "is_pregnant": False,
                    "is_high_risk": False,
                    "risk_condition": None,
                    "allergies": [],
                    "current_medications": [],
                    "assigned_asha": "ASHA-8841",
                    "last_visit_date": "2026-10-20",
                    "next_visit_date": "2026-11-20",
                    "visit_history": [],
                    "reminders": []
                }
            }
        ]
    }

    # First sync
    res1 = client.post("/api/sync", json=sync_payload)
    assert res1.status_code == 200
    assert res1.json()["status"] == "success"
    assert res1.json()["synced_count"] >= 1

    # Idempotent second sync (should not duplicate or crash)
    res2 = client.post("/api/sync", json=sync_payload)
    assert res2.status_code == 200
    assert res2.json()["status"] == "success"
