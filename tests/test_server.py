"""
API integration tests for FastAPI backend server (SyncPulse).
"""

from fastapi.testclient import TestClient
from server.main import app

client = TestClient(app)


def test_api_status():
    resp = client.get("/api/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "online"
    assert data["app_name"] == "SyncPulse"
    assert data["offline_ready"] is True
    assert "stats" in data
    assert data["stats"]["total_registered_households"] == 500


def test_api_ask_escalate():
    resp = client.post("/api/ask", json={"query": "8th month pregnant lady has severe vaginal bleeding"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["type"] == "escalate"
    assert data["primary_citation"] == "DOC-DANG-03#DANG-01"
    assert "REFER IMMEDIATELY" in data["text"]


def test_api_ask_refusal():
    resp = client.post("/api/ask", json={"query": "What dose of amoxicillin should I prescribe for tooth decay?"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["type"] == "refuse"
    assert "paramedical scope" in data["text"].lower() or "outside frontline" in data["text"].lower()


def test_api_ask_in_scope():
    resp = client.post("/api/ask", json={"query": "How to prepare 1 liter of ORS solution?"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["type"] == "answer"
    assert "ORS-02" in data["primary_citation"]
    assert "Protocol Guidance" in data["text"]


def test_api_visits_and_mark_done():
    resp = client.get("/api/visits?limit=10")
    assert resp.status_code == 200
    data = resp.json()
    assert "visits" in data
    assert len(data["visits"]) > 0

    first_hh = data["visits"][0]["household_id"]

    # Mark done
    done_resp = client.post(f"/api/visits/{first_hh}/done", json={"notes": "Checked BP, all normal."})
    assert done_resp.status_code == 200
    assert done_resp.json()["status"] == "success"


def test_api_sync():
    sync_payload = {
        "actions": [
            {
                "client_uuid": "client-uuid-12345",
                "action_type": "MARK_VISITED",
                "household_id": "HH-0005",
                "timestamp": "2026-10-20T10:00:00Z",
                "notes": "Administered Td booster"
            }
        ]
    }
    resp = client.post("/api/sync", json=sync_payload)
    assert resp.status_code == 200
    assert resp.json()["status"] == "success"
    assert resp.json()["synced_count"] >= 1


def test_api_get_patients():
    resp = client.get("/api/patients")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 8
    assert any(p["patient_id"] == "P-101" for p in data)


def test_api_get_patient_detail():
    resp = client.get("/api/patients/P-101")
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Lakshmi Devi"
    assert data["village"] == "Ramnagar"
    assert data["is_pregnant"] is True


def test_api_get_alerts():
    resp = client.get("/api/alerts")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 3
    assert any(a["severity"] == "CRITICAL" for a in data)


def test_api_first_aid_cure():
    resp = client.get("/api/first_aid")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 5
    assert any("Burns" in item["title"] for item in data)


def test_api_health_topics():
    resp = client.get("/api/health_topics")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 3
    assert any("Antenatal Care" in item["title"] for item in data)


def test_static_pwa_served():
    resp = client.get("/")
    assert resp.status_code == 200
    assert "SyncPulse" in resp.text
    assert "app.js" in resp.text
