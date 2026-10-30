"""
Unit tests for the visit prioritization engine and SQLite persistence.
"""

from datetime import date
import pytest
from core.visits import VisitManager


@pytest.fixture
def temp_vm(tmp_path):
    db_file = tmp_path / "test_register.db"
    return VisitManager(str(db_file))


def test_overdue_beats_upcoming(temp_vm):
    visits = temp_vm.get_visit_list(as_of_date=date(2026, 10, 20), limit=50)
    assert len(visits) > 0

    # Ensure all Tier 1 and Tier 2 items appear before Tier 4 items
    tiers = [v.priority_tier for v in visits]
    if "TIER_4_UPCOMING" in tiers:
        first_upcoming_idx = tiers.index("TIER_4_UPCOMING")
        # All items before this must be TIER_1, TIER_2, or TIER_3
        for t in tiers[:first_upcoming_idx]:
            assert t in ("TIER_1_CRITICAL", "TIER_2_OVERDUE", "TIER_3_DUE_TODAY")


def test_high_risk_ranked_tier_1(temp_vm):
    visits = temp_vm.get_visit_list(as_of_date=date(2026, 10, 20), limit=10)
    top_visit = visits[0]
    assert top_visit.priority_tier == "TIER_1_CRITICAL"
    assert top_visit.is_high_risk or top_visit.overdue_days >= 14


def test_village_filter(temp_vm):
    target_village = "Venkatapuram"
    visits = temp_vm.get_visit_list(village=target_village, limit=20)
    assert len(visits) > 0
    for v in visits:
        assert v.village.lower() == target_village.lower()


def test_mark_visited_persistence(temp_vm):
    initial_visits = temp_vm.get_visit_list(limit=5)
    first_hh = initial_visits[0].household_id

    # Mark as completed
    marked = temp_vm.mark_visited(first_hh, notes="Administered Td booster and checked BP.")
    assert marked is True

    # Next call should exclude this household
    updated_visits = temp_vm.get_visit_list(limit=5)
    updated_ids = [v.household_id for v in updated_visits]
    assert first_hh not in updated_ids

    # Query with include_completed=True should show visited=True
    all_visits = temp_vm.get_visit_list(limit=50, include_completed=True)
    matching = [v for v in all_visits if v.household_id == first_hh]
    assert len(matching) == 1
    assert matching[0].visited is True
    assert matching[0].visited_at is not None


def test_daily_cap_limit(temp_vm):
    visits_cap_5 = temp_vm.get_visit_list(limit=5)
    assert len(visits_cap_5) <= 5

    visits_cap_15 = temp_vm.get_visit_list(limit=15)
    assert len(visits_cap_15) <= 15
