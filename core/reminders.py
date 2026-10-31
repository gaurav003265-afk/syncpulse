"""
Monthly Reminders and Follow-up Gap Detector for SyncPulse.

Implements Part E and Part F:
- Generates monthly reminders based strictly on approved MoHFW schedules and actual due dates.
- Detects overdue recorded follow-up tasks from real local data.
- Handles month-end boundaries (Feb 28/29, 30-day months) safely without inventing dates.
- Deduplicates reminders deterministically.
- Clearly states: Local on-device storage only (zero fake push notifications).
"""

from __future__ import annotations

import calendar
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from core.db import DatabaseManager


@dataclass
class MonthlyReminder:
    reminder_id: str
    household_id: str
    village: str
    beneficiary_name: str
    beneficiary_type: str
    service_code: str
    service_name: str
    protocol_citation: str
    due_date: str
    status: str  # "OVERDUE", "DUE_THIS_MONTH", "UPCOMING_NEXT_MONTH", "COMPLETED"
    days_diff: int
    explanation: str
    is_high_risk: bool
    risk_tag: Optional[str]
    is_completed: bool
    completed_at: Optional[str]
    notification_channel: str = "LOCAL_DEVICE_ONLY"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class FollowUpGap:
    follow_up_id: str
    household_id: str
    village: str
    beneficiary_name: str
    task_description: str
    due_date: str
    overdue_days: int
    priority: str
    status: str  # "OVERDUE_GAP", "DUE_TODAY", "UPCOMING"
    created_at: str
    explanation: str
    is_high_risk: bool

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def safe_month_boundary(year: int, month: int, day: int) -> date:
    """Safely clamps day to the maximum valid day in that year and month."""
    max_day = calendar.monthrange(year, month)[1]
    clamped_day = min(day, max_day)
    return date(year, month, clamped_day)


class ReminderService:
    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        self.db = db_manager or DatabaseManager()

    def generate_monthly_reminders(
        self,
        as_of_date_str: str = "2026-10-20",
        month_target: Optional[str] = None,
    ) -> List[MonthlyReminder]:
        """
        Generates reminders for the active month window.
        Uses actual due dates and approved schedules from the database.
        Deduplicates by household_id + service_code + due_date.
        """
        as_of = date.fromisoformat(as_of_date_str)

        # Target month boundaries
        year = as_of.year
        month = as_of.month

        # Month start and end
        month_start = date(year, month, 1)
        month_end = date(year, month, calendar.monthrange(year, month)[1])

        # Next month end
        next_month_year = year if month < 12 else year + 1
        next_month_num = month + 1 if month < 12 else 1
        next_month_end = date(
            next_month_year,
            next_month_num,
            calendar.monthrange(next_month_year, next_month_num)[1],
        )

        query = """
            SELECT 
                h.household_id, h.village, h.beneficiary_name, h.beneficiary_type,
                h.service_code, h.service_name, h.protocol_citation, h.due_date,
                h.is_high_risk, h.risk_tag,
                MAX(v.visited_at) AS visited_at,
                (MAX(v.visited_at) IS NOT NULL) AS is_completed
            FROM households h
            LEFT JOIN (
                SELECT household_id, visited_at FROM visit_outcomes
                UNION ALL
                SELECT household_id, visited_at FROM visit_actions
            ) v ON h.household_id = v.household_id
            GROUP BY h.household_id, h.village, h.beneficiary_name, h.beneficiary_type,
                     h.service_code, h.service_name, h.protocol_citation, h.due_date,
                     h.is_high_risk, h.risk_tag
            ORDER BY h.is_high_risk DESC, h.due_date ASC
        """

        reminders: List[MonthlyReminder] = []
        seen_keys = set()

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            rows = cursor.fetchall()

        for r in rows:
            try:
                due_d = date.fromisoformat(r["due_date"])
            except (ValueError, TypeError):
                continue

            # Deduplication key
            dedup_key = f"{r['household_id']}#{r['service_code']}#{r['due_date']}"
            if dedup_key in seen_keys:
                continue
            seen_keys.add(dedup_key)

            diff_days = (as_of - due_d).days
            is_done = bool(r["is_completed"])
            is_hr = bool(r["is_high_risk"])

            # Classification
            if is_done:
                status = "COMPLETED"
                explanation = f"Completed scheduled visit on {r['visited_at'][:10]}"
            elif diff_days > 0:
                status = "OVERDUE"
                explanation = f"Overdue by {diff_days} days (Due {r['due_date']}) per protocol {r['protocol_citation']}"
            elif month_start <= due_d <= month_end:
                status = "DUE_THIS_MONTH"
                days_left = (due_d - as_of).days
                explanation = f"Due this month in {days_left} days ({r['due_date']}) per {r['protocol_citation']}"
            elif month_end < due_d <= next_month_end:
                status = "UPCOMING_NEXT_MONTH"
                days_left = (due_d - as_of).days
                explanation = f"Upcoming next month ({r['due_date']}) per {r['protocol_citation']}"
            else:
                # Outside monthly planning scope
                continue

            rem_id = f"REM-{r['household_id']}-{r['service_code']}-{r['due_date']}"

            reminders.append(
                MonthlyReminder(
                    reminder_id=rem_id,
                    household_id=r["household_id"],
                    village=r["village"],
                    beneficiary_name=r["beneficiary_name"],
                    beneficiary_type=r["beneficiary_type"],
                    service_code=r["service_code"],
                    service_name=r["service_name"],
                    protocol_citation=r["protocol_citation"],
                    due_date=r["due_date"],
                    status=status,
                    days_diff=diff_days,
                    explanation=explanation,
                    is_high_risk=is_hr,
                    risk_tag=r["risk_tag"],
                    is_completed=is_done,
                    completed_at=r["visited_at"] if is_done else None,
                    notification_channel="LOCAL_DEVICE_ONLY",
                )
            )

        return reminders

    def detect_follow_up_gaps(
        self,
        as_of_date_str: str = "2026-10-20",
    ) -> List[FollowUpGap]:
        """
        Scans recorded follow-up tasks in the database and identifies
        tasks that are overdue or due today.
        Grounds every finding in real database records without inventing outcomes.
        """
        as_of = date.fromisoformat(as_of_date_str)

        query = """
            SELECT 
                f.follow_up_id, f.household_id, f.task_description, f.due_date,
                f.priority, f.status, f.created_at,
                h.village, h.beneficiary_name, h.is_high_risk
            FROM follow_ups f
            JOIN households h ON f.household_id = h.household_id
            WHERE f.status = 'PENDING'
            ORDER BY f.due_date ASC
        """

        gaps: List[FollowUpGap] = []
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            rows = cursor.fetchall()

        for r in rows:
            try:
                due_d = date.fromisoformat(r["due_date"][:10])
            except (ValueError, TypeError):
                continue

            diff_days = (as_of - due_d).days

            if diff_days > 0:
                gap_status = "OVERDUE_GAP"
                explanation = (
                    f"Recorded task overdue by {diff_days} days (Due {r['due_date'][:10]}): "
                    f"'{r['task_description']}'"
                )
            elif diff_days == 0:
                gap_status = "DUE_TODAY"
                explanation = f"Recorded task due today: '{r['task_description']}'"
            else:
                gap_status = "UPCOMING"
                explanation = f"Upcoming task due in {-diff_days} days: '{r['task_description']}'"

            gaps.append(
                FollowUpGap(
                    follow_up_id=r["follow_up_id"],
                    household_id=r["household_id"],
                    village=r["village"],
                    beneficiary_name=r["beneficiary_name"],
                    task_description=r["task_description"],
                    due_date=r["due_date"][:10],
                    overdue_days=max(0, diff_days),
                    priority=r["priority"],
                    status=gap_status,
                    created_at=r["created_at"],
                    explanation=explanation,
                    is_high_risk=bool(r["is_high_risk"]),
                )
            )

        return gaps
