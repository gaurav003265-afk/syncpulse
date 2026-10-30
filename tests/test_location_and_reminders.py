"""
Tests for Location-Aware Planning, Haversine Distance, and Monthly Reminders in SyncPulse.

Verifies:
1. Haversine distance with Earth radius 6371.0 km on known test points.
2. Missing or denied GPS coordinates returning None and "Distance unavailable".
3. Coordinate boundary validation (-90 <= lat <= 90, -180 <= lon <= 180).
4. Clinical urgency primacy: high-risk danger visits (Tier 1) always rank before
   routine visits regardless of physical distance.
5. Secondary tie-breaking: distance is used solely within the same clinical priority tier.
6. Safe month-end boundary handling for monthly reminders (Feb 28/29, 30-day months).
7. Deterministic reminder deduplication and local-only disclosure.
8. Follow-up gap detection for overdue recorded tasks.
9. Database persistence of location updates and outbox audit logging.
"""

from datetime import date, datetime, timezone
import pytest

from core.db import DatabaseManager
from core.location import (
    EARTH_RADIUS_KM,
    Coordinates,
    format_distance_label,
    haversine_distance_km,
    is_valid_coordinate,
)
from core.reminders import ReminderService, safe_month_boundary
from core.repository import SyncPulseRepository
from core.visits import VisitManager


# ---------------------------------------------------------------------------
# 1. Haversine Distance & Coordinate Validation
# ---------------------------------------------------------------------------

def test_haversine_earth_radius():
    assert EARTH_RADIUS_KM == 6371.0


def test_haversine_identical_coordinates():
    # Distance between identical points must be exactly 0.0 km
    lat, lon = 16.5062, 80.6480
    dist = haversine_distance_km(lat, lon, lat, lon)
    assert dist == 0.0


def test_haversine_known_coordinates():
    # Sub-center point: 16.5062, 80.6480
    # Village point: 16.5200, 80.6600
    dist = haversine_distance_km(16.5062, 80.6480, 16.5200, 80.6600)
    assert dist is not None
    # Expected distance is ~2.01 km
    assert 1.95 <= dist <= 2.10

    # Longer reference baseline: London (51.5074, -0.1278) to Paris (48.8566, 2.3522) ~ 343.5 km
    long_dist = haversine_distance_km(51.5074, -0.1278, 48.8566, 2.3522)
    assert long_dist is not None
    assert 340.0 <= long_dist <= 350.0


def test_haversine_missing_or_none_coordinates():
    # If any coordinate is None, distance must return None
    assert haversine_distance_km(None, 80.6480, 16.5200, 80.6600) is None
    assert haversine_distance_km(16.5062, None, 16.5200, 80.6600) is None
    assert haversine_distance_km(16.5062, 80.6480, None, 80.6600) is None
    assert haversine_distance_km(16.5062, 80.6480, 16.5200, None) is None
    assert haversine_distance_km(None, None, None, None) is None


def test_coordinate_validation():
    # Valid boundaries
    assert is_valid_coordinate(0.0, 0.0) is True
    assert is_valid_coordinate(90.0, 180.0) is True
    assert is_valid_coordinate(-90.0, -180.0) is True
    assert is_valid_coordinate(16.5062, 80.6480) is True

    # Invalid coordinates
    assert is_valid_coordinate(90.001, 80.0) is False
    assert is_valid_coordinate(-90.001, 80.0) is False
    assert is_valid_coordinate(16.0, 180.001) is False
    assert is_valid_coordinate(16.0, -180.001) is False
    assert is_valid_coordinate(None, 80.0) is False
    assert is_valid_coordinate("invalid", 80.0) is False


def test_distance_formatting_labels():
    # Missing / None
    assert format_distance_label(None) == "Distance unavailable"

    # Sub-kilometer (< 1 km) in meters
    assert format_distance_label(0.0) == "0 m (straight-line)"
    assert format_distance_label(0.35) == "350 m (straight-line)"
    assert format_distance_label(0.999) == "999 m (straight-line)"

    # Kilometers (>= 1.0 km)
    assert format_distance_label(1.0) == "1.00 km (straight-line)"
    assert format_distance_label(2.456) == "2.46 km (straight-line)"
    assert format_distance_label(15.2) == "15.20 km (straight-line)"

    # Guarantees honest labelling
    label = format_distance_label(3.2)
    assert "(straight-line)" in label
    assert "road" not in label.lower()
    assert "drive" not in label.lower()
    assert "walk" not in label.lower()


# ---------------------------------------------------------------------------
# 2. Prioritization: Clinical Urgency vs Distance
# ---------------------------------------------------------------------------

@pytest.fixture
def temp_db_and_managers(tmp_path):
    db_file = str(tmp_path / "test_location.db")
    db_mgr = DatabaseManager(db_file)
    repo = SyncPulseRepository(db_mgr)
    visit_mgr = VisitManager(db_file)
    reminder_svc = ReminderService(db_mgr)

    # Populate 3 synthetic households with varied clinical urgencies and locations
    with db_mgr.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO households (
                household_id, village, household_head, contact_phone,
                beneficiary_name, beneficiary_type, service_code, service_name,
                protocol_citation, due_date, is_high_risk, risk_tag,
                latitude, longitude, location_source, location_captured_at
            ) VALUES 
            -- HH-001: High Risk (Severe Preeclampsia), FAR AWAY (15.0 km)
            ('HH-001', 'TestVillageAlpha', 'Far HighRisk Head', '9876543210',
             'Anasuya Devi', 'Maternal', 'ANC-03', 'Antenatal Checkup 3',
             'MoHFW Guidelines Sec 3.2', '2026-10-18', 1, 'Severe Preeclampsia (BP 160/110)',
             16.6400, 80.6480, 'MANUAL_ENTRY', '2026-10-19T00:00:00Z'),

            -- HH-002: Routine Due Today, VERY CLOSE (0.15 km)
            ('HH-002', 'TestVillageAlpha', 'Near Routine Head', '9876543211',
             'Bhavani Kumar', 'Infant', 'IMM-02', 'Pentavalent 1',
             'UIP Guidelines Sec 4.1', '2026-10-20', 0, NULL,
             16.5075, 80.6480, 'GPS_CAPTURE', '2026-10-19T00:00:00Z'),

            -- HH-003: Routine Overdue (3 days), MEDIUM DISTANCE (2.0 km)
            ('HH-003', 'TestVillageAlpha', 'Medium Overdue Head', '9876543212',
             'Chitra Rao', 'Maternal', 'ANC-02', 'Antenatal Checkup 2',
             'MoHFW Guidelines Sec 3.1', '2026-10-17', 0, NULL,
             16.5240, 80.6480, 'MANUAL_ENTRY', '2026-10-19T00:00:00Z')
        """)
        conn.commit()

    return db_mgr, repo, visit_mgr, reminder_svc


def test_clinical_urgency_dominates_distance(temp_db_and_managers):
    """
    NON-NEGOTIABLE SAFETY RULE:
    Clinical urgency MUST always take priority over distance.
    A high-risk patient 15 km away MUST be ranked ahead of a routine patient 150 meters away.
    """
    _, _, visit_mgr, _ = temp_db_and_managers
    worker_lat, worker_lon = 16.5062, 80.6480  # Worker at base

    visits = visit_mgr.get_visit_list(
        as_of_date=date(2026, 10, 20),
        village="TestVillageAlpha",
        worker_lat=worker_lat,
        worker_lon=worker_lon,
        limit=10,
    )
    assert len(visits) == 3

    # Ranking 1: HH-001 (High-risk, Tier 1), despite being 14.88 km away
    assert visits[0].household_id == "HH-001"
    assert visits[0].priority_tier == "TIER_1_CRITICAL"
    assert visits[0].straight_line_distance_km > 10.0

    # Ranking 2: HH-003 (Routine Overdue by 3 days, Tier 2), despite being 1.98 km away
    assert visits[1].household_id == "HH-003"
    assert visits[1].priority_tier == "TIER_2_OVERDUE"

    # Ranking 3: HH-002 (Routine Due Today, Tier 3), despite being nearest (0.14 km)
    assert visits[2].household_id == "HH-002"
    assert visits[2].priority_tier == "TIER_3_DUE_TODAY"
    assert visits[2].straight_line_distance_km < 0.2


def test_secondary_distance_tie_breaker_same_tier(temp_db_and_managers):
    """
    Within the SAME priority tier (e.g. both Due Today), straight-line distance
    acts as the secondary tie-breaker (closer visits prioritized).
    """
    db_mgr, _, visit_mgr, _ = temp_db_and_managers
    worker_lat, worker_lon = 16.5062, 80.6480

    # Add two households both Due Today with different distances in a separate test village
    with db_mgr.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO households (
                household_id, village, household_head, contact_phone,
                beneficiary_name, beneficiary_type, service_code, service_name,
                protocol_citation, due_date, is_high_risk, risk_tag,
                latitude, longitude
            ) VALUES 
            ('HH-CLOSE', 'TestVillageBeta', 'Close Head', '9999999991',
             'Beneficiary Close', 'Adult_NCD', 'NCD-BP', 'BP Screening',
             'NCD Sec 2', '2026-10-20', 0, NULL, 16.5070, 80.6480),
            ('HH-FAR', 'TestVillageBeta', 'Far Head', '9999999992',
             'Beneficiary Far', 'Adult_NCD', 'NCD-BP', 'BP Screening',
             'NCD Sec 2', '2026-10-20', 0, NULL, 16.5400, 80.6480)
        """)
        conn.commit()

    # Query only 'today' tab in TestVillageBeta
    visits = visit_mgr.get_visit_list(
        as_of_date=date(2026, 10, 20),
        village="TestVillageBeta",
        worker_lat=worker_lat,
        worker_lon=worker_lon,
        filter_tab="today",
    )
    today_ids = [v.household_id for v in visits]
    assert today_ids == ["HH-CLOSE", "HH-FAR"]


# ---------------------------------------------------------------------------
# 3. Monthly Reminders & Safe Month-End Boundaries
# ---------------------------------------------------------------------------

def test_safe_month_boundary_leap_and_non_leap():
    # Non-leap year February (2026) has 28 days
    assert safe_month_boundary(2026, 2, 31) == date(2026, 2, 28)
    assert safe_month_boundary(2026, 2, 29) == date(2026, 2, 28)
    assert safe_month_boundary(2026, 2, 15) == date(2026, 2, 15)

    # Leap year February (2024) has 29 days
    assert safe_month_boundary(2024, 2, 31) == date(2024, 2, 29)

    # 30-day months (April, June, September, November)
    assert safe_month_boundary(2026, 4, 31) == date(2026, 4, 30)
    assert safe_month_boundary(2026, 6, 31) == date(2026, 6, 30)
    assert safe_month_boundary(2026, 9, 31) == date(2026, 9, 30)
    assert safe_month_boundary(2026, 11, 31) == date(2026, 11, 30)

    # 31-day months (October)
    assert safe_month_boundary(2026, 10, 31) == date(2026, 10, 31)


def test_monthly_reminders_deduplication_and_channels(temp_db_and_managers):
    _, _, _, reminder_svc = temp_db_and_managers

    reminders = reminder_svc.generate_monthly_reminders("2026-10-20")
    assert len(reminders) >= 3

    # Verify deduplication: reminder_ids and keys must be unique
    seen_ids = set()
    for r in reminders:
        assert r.reminder_id not in seen_ids
        seen_ids.add(r.reminder_id)

        # Explicit local device notification disclosure (no fake push notifications)
        assert r.notification_channel == "LOCAL_DEVICE_ONLY"
        assert r.service_code != ""
        assert r.protocol_citation != ""


# ---------------------------------------------------------------------------
# 4. Follow-up Gap Detection
# ---------------------------------------------------------------------------

def test_follow_up_gap_detector(temp_db_and_managers):
    db_mgr, _, _, reminder_svc = temp_db_and_managers

    with db_mgr.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO follow_ups (
                follow_up_id, household_id, task_description, due_date,
                priority, status, created_at
            ) VALUES 
            ('GAP-001', 'HH-001', 'Check repeat BP 48hr post severe alert', '2026-10-16', 'CRITICAL', 'PENDING', '2026-10-14T10:00:00Z'),
            ('GAP-002', 'HH-002', 'Routine follow-up completed', '2026-10-15', 'ROUTINE', 'COMPLETED', '2026-10-13T10:00:00Z')
        """)
        conn.commit()

    gaps = reminder_svc.detect_follow_up_gaps("2026-10-20")
    assert len(gaps) == 1

    gap = gaps[0]
    assert gap.follow_up_id == "GAP-001"
    assert gap.household_id == "HH-001"
    assert gap.status == "OVERDUE_GAP"
    assert gap.overdue_days == 4
    assert "overdue by 4 days" in gap.explanation.lower()


# ---------------------------------------------------------------------------
# 5. Database Persistence & Outbox Logging
# ---------------------------------------------------------------------------

def test_update_household_location_persistence_and_audit(temp_db_and_managers):
    db_mgr, repo, _, _ = temp_db_and_managers

    success = repo.update_household_location(
        household_id="HH-002",
        latitude=16.5188,
        longitude=80.6522,
        accuracy_m=5.2,
        source="GPS_CAPTURE",
    )
    assert success is True

    # Verify updated row in DB
    with db_mgr.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT latitude, longitude, location_accuracy_m, location_source, location_captured_at
            FROM households WHERE household_id = 'HH-002'
        """)
        row = cursor.fetchone()
        assert row is not None
        assert row["latitude"] == 16.5188
        assert row["longitude"] == 80.6522
        assert row["location_accuracy_m"] == 5.2
        assert row["location_source"] == "GPS_CAPTURE"
        assert row["location_captured_at"] is not None

        # Verify sync_outbox event was recorded
        cursor.execute("""
            SELECT entity_type, entity_id, action, payload_json
            FROM sync_outbox 
            WHERE entity_id = 'HH-002' AND action = 'update_location'
        """)
        outbox_row = cursor.fetchone()
        assert outbox_row is not None
        assert outbox_row["entity_type"] == "household"
        assert "16.5188" in outbox_row["payload_json"]


def test_update_household_location_invalid_coords_rejected(temp_db_and_managers):
    _, repo, _, _ = temp_db_and_managers

    with pytest.raises(ValueError) as excinfo:
        repo.update_household_location(
            household_id="HH-002",
            latitude=95.0,  # Invalid latitude (> 90)
            longitude=80.0,
        )
    assert "Invalid geographical coordinates" in str(excinfo.value)
