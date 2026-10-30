"""
SyncPulse SQLite Local Data Layer
Manages persistent offline storage with ACID transactions, WAL mode,
and strict separation between source data and user-entered clinical data.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class HouseholdEntity:
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
    is_high_risk: bool
    risk_tag: Optional[str]
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    location_captured_at: Optional[str] = None
    location_accuracy_m: Optional[float] = None
    location_source: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class BeneficiaryEntity:
    beneficiary_id: str
    household_id: str
    name: str
    beneficiary_type: str
    service_code: str
    service_name: str
    protocol_citation: str
    due_date: str
    is_high_risk: bool
    risk_tag: Optional[str]
    created_at: str
    updated_at: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class VisitOutcomeEntity:
    visit_id: str
    household_id: str
    beneficiary_id: Optional[str]
    visited_at: str
    asha_id: str
    bp_systolic: Optional[int]
    bp_diastolic: Optional[int]
    pulse_bpm: Optional[int]
    temperature_f: Optional[float]
    weight_kg: Optional[float]
    muac_mm: Optional[int]
    service_rendered: str
    visit_outcome: str
    visit_notes: Optional[str]
    is_synced: bool

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class FollowUpEntity:
    follow_up_id: str
    household_id: str
    beneficiary_id: Optional[str]
    task_description: str
    due_date: str
    priority: str  # "CRITICAL", "URGENT", "ROUTINE"
    status: str    # "PENDING", "COMPLETED", "CANCELLED"
    created_at: str
    completed_at: Optional[str]
    completion_notes: Optional[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class EmergencyEventEntity:
    alert_id: str
    patient_id: Optional[str]
    patient_name: str
    village: str
    contact_phone: str
    severity: str  # "CRITICAL", "URGENT", "ROUTINE"
    symptoms: str
    description: Optional[str]
    action_taken: Optional[str]
    delivery_status: str  # "QUEUED_OFFLINE", "DELIVERED", "RESOLVED"
    created_at: str
    resolved_at: Optional[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SyncOutboxEntity:
    event_id: str
    entity_type: str  # "visit", "household", "patient", "follow_up", "emergency_alert"
    entity_id: str
    action: str       # "create", "update", "complete"
    payload: Dict[str, Any]
    created_at: str
    status: str       # "PENDING", "SYNCED", "FAILED"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class DatabaseManager:
    """
    Thread-safe SQLite manager with WAL journal mode, foreign keys enabled,
    and automatic migrations.
    """

    def __init__(self, db_path: Optional[str] = None):
        root_dir = Path(__file__).resolve().parent.parent
        if db_path is None:
            self.db_path = root_dir / "data" / "register.db"
        else:
            self.db_path = Path(db_path)

        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=15.0)
        conn.row_factory = sqlite3.Row
        # Enable foreign key enforcement and WAL mode for reliable offline transactions
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA journal_mode = WAL;")
        return conn

    def _init_schema(self):
        """Creates normalized tables and indices if they do not exist."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # 1. Households (Matches 500-household schema with source columns)
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
                    is_high_risk INTEGER NOT NULL DEFAULT 0,
                    risk_tag TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_hh_village ON households(village);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_hh_due ON households(due_date);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_hh_risk ON households(is_high_risk);")

            # Check and migrate location and audit columns in households table if missing
            cursor.execute("PRAGMA table_info(households);")
            existing_cols = {row["name"] for row in cursor.fetchall()}
            if "latitude" not in existing_cols:
                cursor.execute("ALTER TABLE households ADD COLUMN latitude REAL;")
            if "longitude" not in existing_cols:
                cursor.execute("ALTER TABLE households ADD COLUMN longitude REAL;")
            if "location_captured_at" not in existing_cols:
                cursor.execute("ALTER TABLE households ADD COLUMN location_captured_at TEXT;")
            if "location_accuracy_m" not in existing_cols:
                cursor.execute("ALTER TABLE households ADD COLUMN location_accuracy_m REAL;")
            if "location_source" not in existing_cols:
                cursor.execute("ALTER TABLE households ADD COLUMN location_source TEXT;")
            if "created_at" not in existing_cols:
                cursor.execute("ALTER TABLE households ADD COLUMN created_at TEXT;")
            if "updated_at" not in existing_cols:
                cursor.execute("ALTER TABLE households ADD COLUMN updated_at TEXT;")

            # 2. Beneficiaries / Individual Patient Profiles
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS beneficiaries (
                    beneficiary_id TEXT PRIMARY KEY,
                    household_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    beneficiary_type TEXT NOT NULL,
                    service_code TEXT NOT NULL,
                    service_name TEXT NOT NULL,
                    protocol_citation TEXT NOT NULL,
                    due_date TEXT NOT NULL,
                    is_high_risk INTEGER NOT NULL DEFAULT 0,
                    risk_tag TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (household_id) REFERENCES households(household_id) ON DELETE CASCADE
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_ben_due ON beneficiaries(due_date);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_ben_risk ON beneficiaries(is_high_risk);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_ben_hh ON beneficiaries(household_id);")

            # 3. Visits & Clinical Outcomes (User-entered clinical data)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS visit_outcomes (
                    visit_id TEXT PRIMARY KEY,
                    household_id TEXT NOT NULL,
                    beneficiary_id TEXT,
                    visited_at TEXT NOT NULL,
                    asha_id TEXT NOT NULL DEFAULT 'ASHA-8841',
                    bp_systolic INTEGER,
                    bp_diastolic INTEGER,
                    pulse_bpm INTEGER,
                    temperature_f REAL,
                    weight_kg REAL,
                    muac_mm INTEGER,
                    service_rendered TEXT NOT NULL,
                    visit_outcome TEXT NOT NULL,
                    visit_notes TEXT,
                    is_synced INTEGER NOT NULL DEFAULT 0,
                    FOREIGN KEY (household_id) REFERENCES households(household_id) ON DELETE CASCADE
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_vo_hh ON visit_outcomes(household_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_vo_time ON visit_outcomes(visited_at);")

            # 4. Follow-Up Tasks
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS follow_ups (
                    follow_up_id TEXT PRIMARY KEY,
                    household_id TEXT NOT NULL,
                    beneficiary_id TEXT,
                    task_description TEXT NOT NULL,
                    due_date TEXT NOT NULL,
                    priority TEXT NOT NULL DEFAULT 'ROUTINE',
                    status TEXT NOT NULL DEFAULT 'PENDING',
                    created_at TEXT NOT NULL,
                    completed_at TEXT,
                    completion_notes TEXT,
                    FOREIGN KEY (household_id) REFERENCES households(household_id) ON DELETE CASCADE
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_flw_status ON follow_ups(status);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_flw_due ON follow_ups(due_date);")

            # 5. Emergency Events
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS emergency_events (
                    alert_id TEXT PRIMARY KEY,
                    patient_id TEXT,
                    patient_name TEXT NOT NULL,
                    village TEXT NOT NULL,
                    contact_phone TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    symptoms TEXT NOT NULL,
                    description TEXT,
                    action_taken TEXT,
                    delivery_status TEXT NOT NULL DEFAULT 'QUEUED_OFFLINE',
                    created_at TEXT NOT NULL,
                    resolved_at TEXT
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_emg_status ON emergency_events(delivery_status);")

            # 6. Synchronization Outbox
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sync_outbox (
                    event_id TEXT PRIMARY KEY,
                    entity_type TEXT NOT NULL,
                    entity_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'PENDING'
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_outbox_status ON sync_outbox(status);")

            # 7. Compatibility table: visit_actions (legacy VisitManager compatibility)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS visit_actions (
                    household_id TEXT PRIMARY KEY,
                    visited_at TEXT NOT NULL,
                    visit_notes TEXT,
                    is_synced INTEGER DEFAULT 0
                )
            """)
            conn.commit()


# Singleton repository accessor
_global_db_mgr: Optional[DatabaseManager] = None


def get_db(db_path: Optional[str] = None) -> DatabaseManager:
    global _global_db_mgr
    if db_path is not None:
        return DatabaseManager(db_path)
    if _global_db_mgr is None:
        _global_db_mgr = DatabaseManager()
    return _global_db_mgr
