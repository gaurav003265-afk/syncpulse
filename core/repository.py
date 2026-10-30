"""
SyncPulse Repository Layer
Encapsulates all SQL CRUD operations, ACID transactional updates,
and data integrity constraints for frontline health operations.
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from dataclasses import asdict
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from core.db import (
    BeneficiaryEntity,
    DatabaseManager,
    EmergencyEventEntity,
    FollowUpEntity,
    HouseholdEntity,
    SyncOutboxEntity,
    VisitOutcomeEntity,
    get_db,
)


class SyncPulseRepository:
    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        self.db = db_manager or get_db()

    # --- HOUSEHOLDS & BENEFICIARIES ---

    def search_households(
        self,
        query_str: Optional[str] = None,
        village: Optional[str] = None,
        beneficiary_type: Optional[str] = None,
        is_high_risk: Optional[bool] = None,
        visited_status: Optional[str] = None,  # "visited", "pending", "all"
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[Dict[str, Any]], int]:
        sql = """
            SELECT 
                h.household_id, h.village, h.household_head, h.contact_phone,
                COALESCE(b.beneficiary_id, h.household_id || '-B1') AS beneficiary_id,
                COALESCE(b.name, h.beneficiary_name) AS beneficiary_name,
                COALESCE(b.beneficiary_type, h.beneficiary_type) AS beneficiary_type,
                COALESCE(b.service_code, h.service_code) AS service_code,
                COALESCE(b.service_name, h.service_name) AS service_name,
                COALESCE(b.protocol_citation, h.protocol_citation) AS protocol_citation,
                COALESCE(b.due_date, h.due_date) AS due_date,
                COALESCE(b.is_high_risk, h.is_high_risk) AS is_high_risk,
                COALESCE(b.risk_tag, h.risk_tag) AS risk_tag,
                (v.visited_at IS NOT NULL OR va.visited_at IS NOT NULL) AS is_visited,
                COALESCE(v.visited_at, va.visited_at) AS visited_at,
                COALESCE(v.visit_notes, va.visit_notes) AS visit_notes
            FROM households h
            LEFT JOIN beneficiaries b ON h.household_id = b.household_id
            LEFT JOIN visit_actions va ON h.household_id = va.household_id
            LEFT JOIN (
                SELECT household_id, visited_at, visit_notes, visit_id,
                       ROW_NUMBER() OVER (PARTITION BY household_id ORDER BY visited_at DESC) as rn
                FROM visit_outcomes
            ) v ON h.household_id = v.household_id AND v.rn = 1
            WHERE 1=1
        """
        params: List[Any] = []

        if query_str and query_str.strip():
            term = f"%{query_str.strip()}%"
            sql += """ AND (
                h.household_id LIKE ? OR 
                h.household_head LIKE ? OR 
                h.contact_phone LIKE ? OR 
                COALESCE(b.name, h.beneficiary_name) LIKE ? OR 
                COALESCE(b.service_name, h.service_name) LIKE ?
            )"""
            params.extend([term, term, term, term, term])

        if village and village.lower() != "all":
            sql += " AND LOWER(h.village) = LOWER(?)"
            params.append(village.strip())

        if beneficiary_type and beneficiary_type.lower() != "all":
            sql += " AND LOWER(COALESCE(b.beneficiary_type, h.beneficiary_type)) = LOWER(?)"
            params.append(beneficiary_type.strip())

        if is_high_risk is not None:
            sql += " AND COALESCE(b.is_high_risk, h.is_high_risk) = ?"
            params.append(1 if is_high_risk else 0)

        if visited_status == "visited":
            sql += " AND (v.visited_at IS NOT NULL OR va.visited_at IS NOT NULL)"
        elif visited_status == "pending":
            sql += " AND (v.visited_at IS NULL AND va.visited_at IS NULL)"

        count_sql = f"SELECT COUNT(*) FROM ({sql})"

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(count_sql, params)
            total_count = cursor.fetchone()[0]

            sql += " ORDER BY COALESCE(b.is_high_risk, h.is_high_risk) DESC, COALESCE(b.due_date, h.due_date) ASC, h.household_id ASC LIMIT ? OFFSET ?"
            params.extend([limit, offset])

            cursor.execute(sql, params)
            rows = cursor.fetchall()
            results = [dict(r) for r in rows]

        return results, total_count

    def get_household(self, household_id: str) -> Optional[Dict[str, Any]]:
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM households WHERE household_id = ?", (household_id,))
            hh = cursor.fetchone()
            if not hh:
                return None

            data = dict(hh)

            # Get beneficiaries
            cursor.execute("SELECT * FROM beneficiaries WHERE household_id = ?", (household_id,))
            bens = [dict(r) for r in cursor.fetchall()]
            if not bens and "beneficiary_name" in data:
                bens.append({
                    "beneficiary_id": f"{household_id}-B1",
                    "household_id": household_id,
                    "name": data["beneficiary_name"],
                    "beneficiary_type": data.get("beneficiary_type", "Maternal"),
                    "service_code": data.get("service_code", "ANC_VISIT_1"),
                    "service_name": data.get("service_name", "Protocol Service"),
                    "protocol_citation": data.get("protocol_citation", "[Protocol]"),
                    "due_date": data.get("due_date", "2026-10-30"),
                    "is_high_risk": bool(data.get("is_high_risk")),
                    "risk_tag": data.get("risk_tag"),
                })
            data["beneficiaries"] = bens

            # Get visit outcomes
            cursor.execute("""
                SELECT * FROM visit_outcomes 
                WHERE household_id = ? 
                ORDER BY visited_at DESC
            """, (household_id,))
            data["visit_history"] = [dict(r) for r in cursor.fetchall()]

            # Also check legacy visit_actions if visit_history is empty
            if not data["visit_history"]:
                cursor.execute("SELECT * FROM visit_actions WHERE household_id = ?", (household_id,))
                va = cursor.fetchone()
                if va:
                    data["visit_history"].append({
                        "visit_id": f"LEGACY-{household_id}",
                        "household_id": household_id,
                        "visited_at": va["visited_at"],
                        "service_rendered": data.get("service_name", "Field Visit"),
                        "visit_outcome": va["visit_notes"] or "Routine visit completed",
                        "visit_notes": va["visit_notes"],
                        "asha_id": "ASHA-8841",
                        "is_synced": bool(va["is_synced"]),
                    })

            # Get follow-ups
            cursor.execute("""
                SELECT * FROM follow_ups 
                WHERE household_id = ? 
                ORDER BY due_date ASC
            """, (household_id,))
            data["follow_ups"] = [dict(r) for r in cursor.fetchall()]

        return data

    def update_household_phone(self, household_id: str, new_phone: str) -> bool:
        now_iso = datetime.now(timezone.utc).isoformat()
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE households 
                SET contact_phone = ?, updated_at = ? 
                WHERE household_id = ?
            """, (new_phone, now_iso, household_id))

            if cursor.rowcount > 0:
                self._record_outbox_event(
                    conn,
                    "household",
                    household_id,
                    "update",
                    {"contact_phone": new_phone, "updated_at": now_iso},
                )
                conn.commit()
                return True
        return False

    def update_household_location(
        self,
        household_id: str,
        latitude: float,
        longitude: float,
        accuracy_m: Optional[float] = None,
        source: str = "MANUAL_ENTRY",
    ) -> bool:
        if not (-90.0 <= latitude <= 90.0 and -180.0 <= longitude <= 180.0):
            raise ValueError(f"Invalid geographical coordinates: lat={latitude}, lon={longitude}")

        now_iso = datetime.now(timezone.utc).isoformat()
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE households 
                SET latitude = ?, 
                    longitude = ?, 
                    location_accuracy_m = ?, 
                    location_source = ?, 
                    location_captured_at = ?, 
                    updated_at = ? 
                WHERE household_id = ?
            """, (latitude, longitude, accuracy_m, source, now_iso, now_iso, household_id))

            if cursor.rowcount > 0:
                self._record_outbox_event(
                    conn,
                    "household",
                    household_id,
                    "update_location",
                    {
                        "household_id": household_id,
                        "latitude": latitude,
                        "longitude": longitude,
                        "accuracy_m": accuracy_m,
                        "source": source,
                        "captured_at": now_iso,
                    },
                )
                conn.commit()
                return True
        return False

    # --- VISIT WORKFLOW & CLINICAL OUTCOMES ---

    def record_visit_outcome(
        self,
        household_id: str,
        service_rendered: str,
        visit_outcome: str,
        vitals: Optional[Dict[str, Any]] = None,
        notes: Optional[str] = None,
        follow_up_task: Optional[str] = None,
        follow_up_due_date: Optional[str] = None,
        follow_up_priority: str = "ROUTINE",
        asha_id: str = "ASHA-8841",
    ) -> Dict[str, Any]:
        """
        Atomic transaction recording clinical visit outcome, updating vitals,
        creating optional follow-up task, and logging to sync outbox.
        """
        now_iso = datetime.now(timezone.utc).isoformat()
        visit_id = f"VIS-{uuid.uuid4().hex[:8].upper()}"

        vitals = vitals or {}
        bp_sys = vitals.get("bp_systolic")
        bp_dia = vitals.get("bp_diastolic")
        pulse = vitals.get("pulse_bpm")
        temp = vitals.get("temperature_f")
        weight = vitals.get("weight_kg")
        muac = vitals.get("muac_mm")

        with self.db.get_connection() as conn:
            cursor = conn.cursor()

            # Verify household exists
            cursor.execute("SELECT household_id FROM households WHERE household_id = ?", (household_id,))
            if not cursor.fetchone():
                raise ValueError(f"Household '{household_id}' does not exist.")

            # Find primary beneficiary
            cursor.execute("SELECT beneficiary_id FROM beneficiaries WHERE household_id = ? LIMIT 1", (household_id,))
            ben_row = cursor.fetchone()
            ben_id = ben_row["beneficiary_id"] if ben_row else None

            # 1. Insert Visit Outcome
            cursor.execute("""
                INSERT INTO visit_outcomes (
                    visit_id, household_id, beneficiary_id, visited_at, asha_id,
                    bp_systolic, bp_diastolic, pulse_bpm, temperature_f, weight_kg, muac_mm,
                    service_rendered, visit_outcome, visit_notes, is_synced
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
            """, (
                visit_id, household_id, ben_id, now_iso, asha_id,
                bp_sys, bp_dia, pulse, temp, weight, muac,
                service_rendered, visit_outcome, notes
            ))

            # 2. Maintain compatibility with legacy visit_actions table
            cursor.execute("""
                INSERT OR REPLACE INTO visit_actions (household_id, visited_at, visit_notes, is_synced)
                VALUES (?, ?, ?, 0)
            """, (household_id, now_iso, notes or visit_outcome))

            # 3. Create follow-up task if specified
            follow_up_id = None
            if follow_up_task and follow_up_due_date:
                follow_up_id = f"FLW-{uuid.uuid4().hex[:8].upper()}"
                cursor.execute("""
                    INSERT INTO follow_ups (
                        follow_up_id, household_id, beneficiary_id, task_description,
                        due_date, priority, status, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, 'PENDING', ?)
                """, (follow_up_id, household_id, ben_id, follow_up_task, follow_up_due_date, follow_up_priority, now_iso))

            # 4. Append to Sync Outbox
            outbox_payload = {
                "visit_id": visit_id,
                "household_id": household_id,
                "beneficiary_id": ben_id,
                "visited_at": now_iso,
                "vitals": vitals,
                "service_rendered": service_rendered,
                "visit_outcome": visit_outcome,
                "notes": notes,
                "follow_up_id": follow_up_id,
            }
            self._record_outbox_event(conn, "visit", visit_id, "complete", outbox_payload)

            conn.commit()

        return {
            "success": True,
            "visit_id": visit_id,
            "household_id": household_id,
            "visited_at": now_iso,
            "follow_up_id": follow_up_id,
        }

    # --- FOLLOW-UPS ---

    def get_follow_ups(
        self, household_id: Optional[str] = None, status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        sql = """
            SELECT f.*, h.village, h.household_head, h.contact_phone, b.name as beneficiary_name
            FROM follow_ups f
            JOIN households h ON f.household_id = h.household_id
            LEFT JOIN beneficiaries b ON f.beneficiary_id = b.beneficiary_id
            WHERE 1=1
        """
        params = []
        if household_id:
            sql += " AND f.household_id = ?"
            params.append(household_id)
        if status and status.lower() != "all":
            sql += " AND LOWER(f.status) = LOWER(?)"
            params.append(status.strip())

        sql += " ORDER BY f.due_date ASC"

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, params)
            return [dict(r) for r in cursor.fetchall()]

    def complete_follow_up(self, follow_up_id: str, completion_notes: str = "") -> bool:
        now_iso = datetime.now(timezone.utc).isoformat()
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE follow_ups
                SET status = 'COMPLETED', completed_at = ?, completion_notes = ?
                WHERE follow_up_id = ?
            """, (now_iso, completion_notes, follow_up_id))

            if cursor.rowcount > 0:
                self._record_outbox_event(
                    conn,
                    "follow_up",
                    follow_up_id,
                    "complete",
                    {"status": "COMPLETED", "completed_at": now_iso, "notes": completion_notes},
                )
                conn.commit()
                return True
        return False

    # --- EMERGENCY EVENTS ---

    def record_emergency_event(self, event_data: Dict[str, Any]) -> str:
        alert_id = event_data.get("alert_id") or f"ALT-{uuid.uuid4().hex[:8].upper()}"
        now_iso = datetime.now(timezone.utc).isoformat()

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO emergency_events (
                    alert_id, patient_id, patient_name, village, contact_phone,
                    severity, symptoms, description, action_taken, delivery_status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                alert_id,
                event_data.get("patient_id"),
                event_data["patient_name"],
                event_data["village"],
                event_data["contact_phone"],
                event_data.get("severity", "CRITICAL"),
                event_data["symptoms"],
                event_data.get("description"),
                event_data.get("action_taken"),
                event_data.get("delivery_status", "QUEUED_OFFLINE"),
                now_iso,
            ))

            self._record_outbox_event(conn, "emergency_alert", alert_id, "create", event_data)
            conn.commit()

        return alert_id

    def get_emergency_events(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        sql = "SELECT * FROM emergency_events WHERE 1=1"
        params = []
        if status and status.lower() != "all":
            sql += " AND LOWER(delivery_status) = LOWER(?)"
            params.append(status.strip())

        sql += " ORDER BY created_at DESC"
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, params)
            return [dict(r) for r in cursor.fetchall()]

    # --- OUTBOX & SYNC ---

    def get_pending_outbox(self) -> List[Dict[str, Any]]:
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM sync_outbox WHERE status = 'PENDING' ORDER BY created_at ASC")
            rows = cursor.fetchall()
            out = []
            for r in rows:
                item = dict(r)
                item["payload"] = json.loads(item["payload_json"])
                out.append(item)
            return out

    def mark_outbox_synced(self, event_ids: List[str]) -> int:
        if not event_ids:
            return 0
        placeholders = ",".join("?" for _ in event_ids)
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"UPDATE sync_outbox SET status = 'SYNCED' WHERE event_id IN ({placeholders})", event_ids)
            count = cursor.rowcount
            conn.commit()
            return count

    def _record_outbox_event(
        self, conn: sqlite3.Connection, entity_type: str, entity_id: str, action: str, payload: Dict[str, Any]
    ):
        event_id = f"evt_{uuid.uuid4().hex}"
        now_iso = datetime.now(timezone.utc).isoformat()
        conn.execute("""
            INSERT INTO sync_outbox (event_id, entity_type, entity_id, action, payload_json, created_at, status)
            VALUES (?, ?, ?, ?, ?, ?, 'PENDING')
        """, (event_id, entity_type, entity_id, action, json.dumps(payload), now_iso))
