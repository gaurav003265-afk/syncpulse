"""
Daily visit prioritization and register management engine.

Provides:
- SQLite persistence (data/register.db) for offline-first resilience.
- Multi-tier clinical prioritization based on MoHFW ANC & immunization schedules:
  * Tier 1: CRITICAL_HIGH_RISK (High-risk medical flag or critically overdue > 14 days)
  * Tier 2: OVERDUE_ROUTINE (Overdue by 1 to 14 days)
  * Tier 3: DUE_TODAY (Due on current visit date)
  * Tier 4: UPCOMING_WEEK (Due in next 1 to 7 days)
- Transparent explainability: Each visit row details WHAT is due, WHY it ranks there,
  and the exact protocol section citation.
- Village / area filtering, configurable daily cap, and mark-as-visited action.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


from core.location import format_distance_label, haversine_distance_km


@dataclass
class VisitItem:
    household_id: str
    village: str
    household_head: str
    contact_phone: str
    beneficiary_name: str
    beneficiary_type: str
    service_code: str
    service_name: str
    protocol_citation: str
    due_date: str
    overdue_days: int
    is_high_risk: bool
    risk_tag: Optional[str]
    priority_tier: str
    priority_rank: int
    priority_reason: str
    visited: bool
    visited_at: Optional[str]
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    location_captured: bool = False
    straight_line_distance_km: Optional[float] = None
    distance_display: str = "Distance unavailable"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class VisitManager:
    def __init__(self, db_path: Optional[str] = None):
        root_dir = Path(__file__).resolve().parent.parent
        if db_path is None:
            self.db_path = root_dir / "data" / "register.db"
        else:
            self.db_path = Path(db_path)

        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """Initializes tables and populates from synthetic register if empty."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS households (
                    household_id TEXT PRIMARY KEY,
                    village TEXT NOT NULL,
                    household_head TEXT NOT NULL,
                    contact_phone TEXT NOT NULL,
                    beneficiary_name TEXT NOT NULL,
                    beneficiary_type TEXT NOT NULL,
                    service_code TEXT NOT NULL,
                    service_name TEXT NOT NULL,
                    protocol_citation TEXT NOT NULL,
                    due_date TEXT NOT NULL,
                    is_high_risk INTEGER NOT NULL,
                    risk_tag TEXT,
                    latitude REAL,
                    longitude REAL,
                    location_captured_at TEXT
                )
            """)

            # Run migration in case table was created with older schema
            cursor.execute("PRAGMA table_info(households);")
            cols = {row["name"] for row in cursor.fetchall()}
            if "latitude" not in cols:
                cursor.execute("ALTER TABLE households ADD COLUMN latitude REAL;")
            if "longitude" not in cols:
                cursor.execute("ALTER TABLE households ADD COLUMN longitude REAL;")
            if "location_captured_at" not in cols:
                cursor.execute("ALTER TABLE households ADD COLUMN location_captured_at TEXT;")

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS visit_actions (
                    household_id TEXT PRIMARY KEY,
                    visited_at TEXT NOT NULL,
                    visit_notes TEXT,
                    is_synced INTEGER DEFAULT 0
                )
            """)

            # Check if households table is populated
            cursor.execute("SELECT COUNT(*) FROM households")
            count = cursor.fetchone()[0]

            if count == 0:
                self._seed_households(cursor)
                conn.commit()

    def _seed_households(self, cursor: sqlite3.Cursor):
        """Seeds initial 500 households from data/synthetic_register/households.json."""
        root_dir = Path(__file__).resolve().parent.parent
        reg_json = root_dir / "data" / "synthetic_register" / "households.json"

        if not reg_json.exists():
            from data.synthetic_register.generate_register import generate_households
            reg_json = generate_households()

        with open(reg_json, "r", encoding="utf-8") as f:
            records = json.load(f)

        for r in records:
            cursor.execute("""
                INSERT OR REPLACE INTO households (
                    household_id, village, household_head, contact_phone,
                    beneficiary_name, beneficiary_type, service_code, service_name,
                    protocol_citation, due_date, is_high_risk, risk_tag
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                r["household_id"], r["village"], r["household_head"], r["contact_phone"],
                r["beneficiary_name"], r["beneficiary_type"], r["service_code"], r["service_name"],
                r["protocol_citation"], r["due_date"], 1 if r["is_high_risk"] else 0, r.get("risk_tag")
            ))

    def get_visit_list(
        self,
        as_of_date: Optional[date] = None,
        village: Optional[str] = None,
        limit: int = 25,
        include_completed: bool = False,
        worker_lat: Optional[float] = None,
        worker_lon: Optional[float] = None,
        filter_tab: str = "all",
    ) -> List[VisitItem]:
        """
        Generates the prioritized daily visit list for an ASHA worker.
        Clinical urgency ALWAYS dominates distance. Straight-line distance
        is used solely as a secondary convenience tie-breaker within the same tier.
        """
        ref_date = as_of_date or date(2026, 10, 20)

        query = """
            SELECT 
                h.household_id, h.village, h.household_head, h.contact_phone,
                h.beneficiary_name, h.beneficiary_type, h.service_code, h.service_name,
                h.protocol_citation, h.due_date, h.is_high_risk, h.risk_tag,
                h.latitude, h.longitude, h.location_captured_at,
                v.visited_at, (v.household_id IS NOT NULL) AS visited
            FROM households h
            LEFT JOIN visit_actions v ON h.household_id = v.household_id
            WHERE 1=1
        """
        params = []

        if not include_completed and filter_tab != "completed":
            query += " AND v.household_id IS NULL"

        if village and village.strip() and village.lower() != "all":
            query += " AND LOWER(h.village) = LOWER(?)"
            params.append(village.strip())

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()

        scored_items: List[VisitItem] = []

        for r in rows:
            is_visited = bool(r["visited"])

            # Filter tab handling
            if filter_tab == "completed" and not is_visited:
                continue

            due_d = date.fromisoformat(r["due_date"])
            diff_days = (ref_date - due_d).days  # positive = overdue, negative = future
            is_hr = bool(r["is_high_risk"])

            if filter_tab == "today" and diff_days != 0:
                continue
            if filter_tab == "overdue" and diff_days <= 0:
                continue
            if filter_tab == "upcoming" and diff_days >= 0:
                continue

            # ---------------------------------------------------------
            # Prioritization Logic (Tiered System)
            # ---------------------------------------------------------
            if is_hr or diff_days >= 14:
                tier = "TIER_1_CRITICAL"
                # Rank score: base 1000 + overdue days + bonus for high-risk
                base_score = 1000 + (100 if is_hr else 0) + diff_days
                reason = "High-risk alert" if is_hr else ""
                if diff_days > 0:
                    reason += f" (Overdue by {diff_days} days)" if reason else f"Critically overdue by {diff_days} days"
                if r["risk_tag"]:
                    reason += f" [{r['risk_tag']}]"

            elif diff_days > 0:
                tier = "TIER_2_OVERDUE"
                base_score = 500 + diff_days
                reason = f"Routine schedule overdue by {diff_days} days"

            elif diff_days == 0:
                tier = "TIER_3_DUE_TODAY"
                base_score = 200
                reason = "Routine schedule due today"

            elif diff_days >= -7 or filter_tab == "upcoming":
                tier = "TIER_4_UPCOMING"
                base_score = 100 + diff_days  # higher score if closer to today
                reason = f"Upcoming routine visit due in {-diff_days} days"

            else:
                # Due beyond 7 days into future -> not priority for this week unless explicitly filtered
                if filter_tab not in ("all", "upcoming"):
                    continue
                tier = "TIER_4_UPCOMING"
                base_score = 50 + diff_days
                reason = f"Upcoming visit due on {r['due_date']}"

            # Location distance calculation
            hh_lat = r["latitude"]
            hh_lon = r["longitude"]
            dist_km = haversine_distance_km(worker_lat, worker_lon, hh_lat, hh_lon)
            dist_label = format_distance_label(dist_km)

            scored_items.append(
                VisitItem(
                    household_id=r["household_id"],
                    village=r["village"],
                    household_head=r["household_head"],
                    contact_phone=r["contact_phone"],
                    beneficiary_name=r["beneficiary_name"],
                    beneficiary_type=r["beneficiary_type"],
                    service_code=r["service_code"],
                    service_name=r["service_name"],
                    protocol_citation=r["protocol_citation"],
                    due_date=r["due_date"],
                    overdue_days=diff_days,
                    is_high_risk=is_hr,
                    risk_tag=r["risk_tag"],
                    priority_tier=tier,
                    priority_rank=base_score,
                    priority_reason=reason.strip(),
                    visited=is_visited,
                    visited_at=r["visited_at"],
                    latitude=hh_lat,
                    longitude=hh_lon,
                    location_captured=hh_lat is not None and hh_lon is not None,
                    straight_line_distance_km=dist_km,
                    distance_display=dist_label,
                )
            )

        # Deterministic Sorting:
        # 1. Higher priority_rank first (descending) -> Clinical Urgency Dominance
        # 2. Straight-line distance ascending (secondary tie-breaker when available)
        # 3. Overdue days descending
        # 4. Deterministic tie-break by household_id ascending
        def _hh_sort_key(hh_id: str):
            digits = "".join(ch for ch in hh_id if ch.isdigit())
            return (int(digits) if digits else 0, hh_id)

        scored_items.sort(
            key=lambda x: (
                -x.priority_rank,
                x.straight_line_distance_km if x.straight_line_distance_km is not None else 999999.0,
                -x.overdue_days,
                _hh_sort_key(x.household_id),
            )
        )

        return scored_items[:limit]

    def mark_visited(self, household_id: str, notes: str = "") -> bool:
        """
        Marks a household visit as completed and persists to SQLite.
        """
        now_iso = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO visit_actions (household_id, visited_at, visit_notes, is_synced)
                VALUES (?, ?, ?, 0)
            """, (household_id, now_iso, notes))
            success = cursor.rowcount > 0

            try:
                visit_id = f"VIS-{household_id}-{int(datetime.now(timezone.utc).timestamp())}"
                cursor.execute("""
                    INSERT OR REPLACE INTO visit_outcomes (
                        visit_id, household_id, visited_at, asha_id, service_rendered, visit_outcome, visit_notes, is_synced
                    ) VALUES (?, ?, ?, 'ASHA-8841', 'Protocol Field Visit', ?, ?, 0)
                """, (visit_id, household_id, now_iso, notes or "Visit completed", notes))
            except Exception:
                pass

            conn.commit()
            return success

    def reset_all_visits(self):
        """Resets all completed visits (useful for clean demo runs)."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM visit_actions")
            conn.commit()

    def get_summary_stats(self, as_of_date: Optional[date] = None) -> Dict[str, Any]:
        """Provides summary metrics for status dashboard."""
        ref_date = as_of_date or date(2026, 10, 20)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM households")
            total_hh = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM visit_actions")
            completed_hh = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(DISTINCT village) FROM households")
            villages_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM households WHERE is_high_risk = 1")
            high_risk_count = cursor.fetchone()[0]

        return {
            "total_registered_households": total_hh,
            "completed_visits": completed_hh,
            "pending_visits": total_hh - completed_hh,
            "high_risk_households": high_risk_count,
            "villages_covered": villages_count,
            "as_of_date": ref_date.isoformat(),
        }


if __name__ == "__main__":
    vm = VisitManager()
    stats = vm.get_summary_stats()
    print("Visit Manager initialized. Register summary:")
    print(f" - Total Households: {stats['total_registered_households']}")
    print(f" - High-Risk Count : {stats['high_risk_households']}")
    print(f" - Completed Visits: {stats['completed_visits']}")

    visits = vm.get_visit_list(limit=5)
    print("\nTop 5 Prioritized Visits for Today:")
    for v in visits:
        print(f" - [{v.priority_tier}] {v.beneficiary_name} ({v.village}) | {v.service_name} -> {v.priority_reason}")
