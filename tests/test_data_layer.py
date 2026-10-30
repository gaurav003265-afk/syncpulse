"""
Comprehensive test suite for the SyncPulse local data layer:
- Repeatable register importer with strict validation
- Duplicate prevention (idempotency)
- Malformed row rejection with specific errors
- Visit outcome recording with clinical vitals
- Follow-up task creation and completion
- Persistence across application restart (reconnection to SQLite)
- ACID transaction integrity
"""

import json
from pathlib import Path
import pytest

from core.db import DatabaseManager
from core.importer import RegisterImporter
from core.repository import SyncPulseRepository


@pytest.fixture
def test_db_path(tmp_path):
    return str(tmp_path / "syncpulse_test.db")


@pytest.fixture
def test_db(test_db_path):
    return DatabaseManager(test_db_path)


@pytest.fixture
def repo(test_db):
    return SyncPulseRepository(test_db)


@pytest.fixture
def importer(test_db):
    return RegisterImporter(test_db)


def test_import_actual_supplied_register(importer, repo):
    """
    Imports the actual 500-household register and verifies exact counts.
    """
    root_dir = Path(__file__).resolve().parent.parent
    reg_path = root_dir / "data" / "synthetic_register" / "households.json"
    assert reg_path.exists(), f"Source register not found at {reg_path}"

    report = importer.import_from_file(reg_path)
    assert report.total_records == 500
    assert report.imported_new == 500
    assert report.updated_existing == 0
    assert report.rejected_count == 0
    assert len(report.errors) == 0

    # Verify count in repository
    results, total = repo.search_households(limit=10)
    assert total == 500
    assert len(results) == 10


def test_duplicate_import_does_not_duplicate_households(importer, repo):
    """
    Re-importing the same register must be idempotent: updates existing records
    without creating duplicate rows or increasing total count.
    """
    root_dir = Path(__file__).resolve().parent.parent
    reg_path = root_dir / "data" / "synthetic_register" / "households.json"

    # First import
    report1 = importer.import_from_file(reg_path)
    assert report1.imported_new == 500

    # Second import of identical file
    report2 = importer.import_from_file(reg_path)
    assert report2.total_records == 500
    assert report2.imported_new == 0
    assert report2.updated_existing == 500
    assert report2.rejected_count == 0

    # Total in DB must remain exactly 500
    _, total = repo.search_households(limit=1)
    assert total == 500


def test_validation_rejects_malformed_records(importer, repo):
    """
    Verifies that rows with missing IDs, invalid phone numbers, bad dates,
    or unsupported beneficiary types are rejected with descriptive errors.
    """
    malformed_data = [
        # Missing household_id
        {
            "household_id": "",
            "village": "Venkatapuram",
            "household_head": "Srinivas",
            "contact_phone": "9876543210",
            "beneficiary_name": "Lakshmi",
            "beneficiary_type": "Maternal",
            "service_code": "ANC_VISIT_1",
            "due_date": "2026-10-20",
            "is_high_risk": False,
        },
        # Invalid phone (<10 digits)
        {
            "household_id": "HH-9901",
            "village": "Venkatapuram",
            "household_head": "Srinivas",
            "contact_phone": "12345",
            "beneficiary_name": "Lakshmi",
            "beneficiary_type": "Maternal",
            "service_code": "ANC_VISIT_1",
            "due_date": "2026-10-20",
            "is_high_risk": False,
        },
        # Invalid due_date format
        {
            "household_id": "HH-9902",
            "village": "Venkatapuram",
            "household_head": "Srinivas",
            "contact_phone": "9876543210",
            "beneficiary_name": "Lakshmi",
            "beneficiary_type": "Maternal",
            "service_code": "ANC_VISIT_1",
            "due_date": "20-10-2026",  # wrong format
            "is_high_risk": False,
        },
        # Invalid beneficiary type
        {
            "household_id": "HH-9903",
            "village": "Venkatapuram",
            "household_head": "Srinivas",
            "contact_phone": "9876543210",
            "beneficiary_name": "Lakshmi",
            "beneficiary_type": "UnknownExtraneousType",
            "service_code": "ANC_VISIT_1",
            "due_date": "2026-10-20",
            "is_high_risk": False,
        },
        # Valid row
        {
            "household_id": "HH-9904",
            "village": "Venkatapuram",
            "household_head": "Valid Head",
            "contact_phone": "9876543210",
            "beneficiary_name": "Valid Beneficiary",
            "beneficiary_type": "Maternal",
            "service_code": "ANC_VISIT_1",
            "due_date": "2026-10-20",
            "is_high_risk": False,
        },
    ]

    report = importer.import_records(malformed_data)
    assert report.total_records == 5
    assert report.imported_new == 1
    assert report.rejected_count == 4
    assert len(report.errors) == 4

    error_fields = [e.field for e in report.errors]
    assert "household_id" in error_fields
    assert "contact_phone" in error_fields
    assert "due_date" in error_fields
    assert "beneficiary_type" in error_fields


def test_search_and_open_real_imported_record(importer, repo):
    """
    Verifies searching by ID, head, village, and opening complete record.
    """
    root_dir = Path(__file__).resolve().parent.parent
    importer.import_from_file(root_dir / "data" / "synthetic_register" / "households.json")

    # Search for HH-0001
    results, total = repo.search_households(query_str="HH-0001")
    assert total >= 1
    hh1 = results[0]
    assert hh1["household_id"] == "HH-0001"

    # Open full household profile
    profile = repo.get_household("HH-0001")
    assert profile is not None
    assert profile["household_id"] == "HH-0001"
    assert len(profile["beneficiaries"]) >= 1
    assert profile["beneficiaries"][0]["household_id"] == "HH-0001"


def test_visit_workflow_with_vitals_and_follow_up(importer, repo):
    """
    Verifies recording clinical visit outcomes, capturing vitals, and creating follow-ups.
    """
    root_dir = Path(__file__).resolve().parent.parent
    importer.import_from_file(root_dir / "data" / "synthetic_register" / "households.json")

    vitals = {
        "bp_systolic": 130,
        "bp_diastolic": 85,
        "pulse_bpm": 78,
        "temperature_f": 98.4,
        "weight_kg": 56.5,
        "muac_mm": None,
    }

    res = repo.record_visit_outcome(
        household_id="HH-0005",
        service_rendered="ANC Checkup & Td Booster",
        visit_outcome="Maternal BP checked, fetal movement confirmed normal, dispensed IFA 30 tablets.",
        vitals=vitals,
        notes="Advised mother on dietary iron and institutional delivery plan.",
        follow_up_task="Check BP in 2 weeks at sub-center clinic",
        follow_up_due_date="2026-11-04",
        follow_up_priority="ROUTINE",
    )

    assert res["success"] is True
    assert res["visit_id"].startswith("VIS-")
    assert res["follow_up_id"].startswith("FLW-")

    # Verify visit appears in household profile history
    profile = repo.get_household("HH-0005")
    assert len(profile["visit_history"]) == 1
    vh = profile["visit_history"][0]
    assert vh["bp_systolic"] == 130
    assert vh["bp_diastolic"] == 85
    assert "IFA 30 tablets" in vh["visit_outcome"]

    # Verify follow-up task exists
    assert len(profile["follow_ups"]) == 1
    flw = profile["follow_ups"][0]
    assert flw["due_date"] == "2026-11-04"
    assert flw["status"] == "PENDING"
    assert "Check BP" in flw["task_description"]

    # Complete the follow-up task
    completed = repo.complete_follow_up(flw["follow_up_id"], completion_notes="BP measured 120/80 normal.")
    assert completed is True

    # Check updated status
    updated_flws = repo.get_follow_ups(household_id="HH-0005")
    assert updated_flws[0]["status"] == "COMPLETED"
    assert updated_flws[0]["completion_notes"] == "BP measured 120/80 normal."


def test_persistence_across_application_restart(test_db_path, tmp_path):
    """
    Verifies that data written to SQLite persists cleanly across app restart
    (simulated by closing connections and instantiating a fresh DatabaseManager).
    """
    root_dir = Path(__file__).resolve().parent.parent
    reg_path = root_dir / "data" / "synthetic_register" / "households.json"

    # Session 1: Boot app, import register, record visit & follow-up
    db1 = DatabaseManager(test_db_path)
    importer1 = RegisterImporter(db1)
    repo1 = SyncPulseRepository(db1)

    importer1.import_from_file(reg_path)
    repo1.record_visit_outcome(
        household_id="HH-0010",
        service_rendered="DPT Booster-1",
        visit_outcome="Vaccination administered successfully, zero adverse reaction.",
        vitals={"temperature_f": 98.6},
        follow_up_task="Check for swelling or fever 48h",
        follow_up_due_date="2026-10-22",
    )
    # Simulate full process exit / connection teardown
    del repo1
    del importer1
    del db1

    # Session 2: Cold boot from the same SQLite file
    db2 = DatabaseManager(test_db_path)
    repo2 = SyncPulseRepository(db2)

    # Verify 500 households persist
    _, total = repo2.search_households(limit=1)
    assert total == 500

    # Verify HH-0010 visit and follow-up persist intact
    hh = repo2.get_household("HH-0010")
    assert hh is not None
    assert len(hh["visit_history"]) == 1
    assert "Vaccination administered" in hh["visit_history"][0]["visit_outcome"]
    assert len(hh["follow_ups"]) == 1
    assert hh["follow_ups"][0]["due_date"] == "2026-10-22"
