"""
Repeatable, idempotent importer for the synthetic household register.
Validates records against approved clinical schemas, prevents duplicate creation,
preserves user-recorded clinical visits, and returns a detailed validation report.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from core.db import DatabaseManager, get_db

VALID_BENEFICIARY_TYPES = {
    "Maternal",
    "Infant",
    "Adult_NCD",
    "Child",
    "Pregnant Woman",
    "Adolescent",
}

PHONE_REGEX = re.compile(r"^\d{10}$")
HH_ID_REGEX = re.compile(r"^HH-\d{4,}$")


@dataclass
class ImportErrorDetail:
    row_index: int
    household_id: Optional[str]
    field: str
    error: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ImportReport:
    total_records: int
    imported_new: int
    updated_existing: int
    rejected_count: int
    errors: List[ImportErrorDetail]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_records": self.total_records,
            "imported_new": self.imported_new,
            "updated_existing": self.updated_existing,
            "rejected_count": self.rejected_count,
            "errors": [e.to_dict() for e in self.errors],
        }


class RegisterImporter:
    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        self.db = db_manager or get_db()

    def validate_record(self, raw: Any, row_idx: int) -> Tuple[bool, List[ImportErrorDetail], Optional[Dict[str, Any]]]:
        errors: List[ImportErrorDetail] = []
        if not isinstance(raw, dict):
            errors.append(ImportErrorDetail(row_idx, None, "record", "Row must be a valid JSON dictionary."))
            return False, errors, None

        hh_id = str(raw.get("household_id", "")).strip()
        if not hh_id or not HH_ID_REGEX.match(hh_id):
            errors.append(
                ImportErrorDetail(row_idx, hh_id or None, "household_id", "Must follow format 'HH-XXXX' with 4+ digits.")
            )

        village = str(raw.get("village", "")).strip()
        if not village or len(village) < 2:
            errors.append(ImportErrorDetail(row_idx, hh_id, "village", "Village name is required (min 2 chars)."))

        head = str(raw.get("household_head", "")).strip()
        if not head or len(head) < 2:
            errors.append(ImportErrorDetail(row_idx, hh_id, "household_head", "Household head name is required."))

        phone = str(raw.get("contact_phone", "")).strip()
        if not phone or not PHONE_REGEX.match(phone):
            errors.append(
                ImportErrorDetail(row_idx, hh_id, "contact_phone", "Contact phone must be exactly 10 digits.")
            )

        b_name = str(raw.get("beneficiary_name", "")).strip()
        if not b_name or len(b_name) < 2:
            errors.append(ImportErrorDetail(row_idx, hh_id, "beneficiary_name", "Beneficiary name is required."))

        b_type = str(raw.get("beneficiary_type", "")).strip()
        if b_type not in VALID_BENEFICIARY_TYPES:
            errors.append(
                ImportErrorDetail(
                    row_idx,
                    hh_id,
                    "beneficiary_type",
                    f"Must be one of {sorted(list(VALID_BENEFICIARY_TYPES))}.",
                )
            )

        due_date_str = str(raw.get("due_date", "")).strip()
        try:
            date.fromisoformat(due_date_str)
        except (ValueError, TypeError):
            errors.append(
                ImportErrorDetail(row_idx, hh_id, "due_date", "Must be a valid ISO8601 date 'YYYY-MM-DD'.")
            )

        service_code = str(raw.get("service_code", "")).strip()
        if not service_code:
            errors.append(ImportErrorDetail(row_idx, hh_id, "service_code", "Protocol service code is required."))

        is_hr = raw.get("is_high_risk")
        if not isinstance(is_hr, (bool, int)):
            errors.append(ImportErrorDetail(row_idx, hh_id, "is_high_risk", "Must be boolean true/false or 0/1."))

        if errors:
            return False, errors, None

        cleaned = {
            "household_id": hh_id,
            "village": village,
            "household_head": head,
            "contact_phone": phone,
            "beneficiary_name": b_name,
            "beneficiary_type": b_type,
            "service_code": service_code,
            "service_name": str(raw.get("service_name", service_code)).strip(),
            "protocol_citation": str(raw.get("protocol_citation", "[Approved Protocol Source]")).strip(),
            "due_date": due_date_str,
            "is_high_risk": 1 if bool(is_hr) else 0,
            "risk_tag": str(raw.get("risk_tag")).strip() if raw.get("risk_tag") else None,
        }
        return True, [], cleaned

    def import_records(self, raw_records: List[Dict[str, Any]]) -> ImportReport:
        """
        Executes an atomic SQLite transaction importing validated households.
        Guarantees that re-importing the same dataset updates metadata without duplicating
        records or losing previously conducted visits.
        """
        now_iso = datetime.now(timezone.utc).isoformat()
        all_errors: List[ImportErrorDetail] = []
        valid_records: List[Dict[str, Any]] = []

        for idx, item in enumerate(raw_records, start=1):
            is_valid, errs, cleaned = self.validate_record(item, idx)
            if is_valid and cleaned:
                valid_records.append(cleaned)
            else:
                all_errors.extend(errs)

        new_count = 0
        updated_count = 0

        with self.db.get_connection() as conn:
            cursor = conn.cursor()

            for rec in valid_records:
                hh_id = rec["household_id"]

                # Check if household exists
                cursor.execute("SELECT household_id FROM households WHERE household_id = ?", (hh_id,))
                row = cursor.fetchone()

                if row is None:
                    # Insert new household
                    cursor.execute("""
                        INSERT INTO households (
                            household_id, village, household_head, contact_phone,
                            beneficiary_name, beneficiary_type, service_code, service_name,
                            protocol_citation, due_date, is_high_risk, risk_tag,
                            created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        hh_id, rec["village"], rec["household_head"], rec["contact_phone"],
                        rec["beneficiary_name"], rec["beneficiary_type"], rec["service_code"], rec["service_name"],
                        rec["protocol_citation"], rec["due_date"], rec["is_high_risk"], rec["risk_tag"],
                        now_iso, now_iso
                    ))

                    # Insert corresponding beneficiary record
                    ben_id = f"{hh_id}-B1"
                    cursor.execute("""
                        INSERT INTO beneficiaries (
                            beneficiary_id, household_id, name, beneficiary_type,
                            service_code, service_name, protocol_citation, due_date,
                            is_high_risk, risk_tag, created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        ben_id, hh_id, rec["beneficiary_name"], rec["beneficiary_type"],
                        rec["service_code"], rec["service_name"], rec["protocol_citation"], rec["due_date"],
                        rec["is_high_risk"], rec["risk_tag"], now_iso, now_iso
                    ))
                    new_count += 1
                else:
                    # Existing household: update demographic and service fields while preserving history
                    cursor.execute("""
                        UPDATE households
                        SET village = ?, household_head = ?, contact_phone = ?,
                            beneficiary_name = ?, beneficiary_type = ?, service_code = ?, service_name = ?,
                            protocol_citation = ?, due_date = ?, is_high_risk = ?, risk_tag = ?, updated_at = ?
                        WHERE household_id = ?
                    """, (
                        rec["village"], rec["household_head"], rec["contact_phone"],
                        rec["beneficiary_name"], rec["beneficiary_type"], rec["service_code"], rec["service_name"],
                        rec["protocol_citation"], rec["due_date"], rec["is_high_risk"], rec["risk_tag"],
                        now_iso, hh_id
                    ))

                    ben_id = f"{hh_id}-B1"
                    cursor.execute("""
                        INSERT INTO beneficiaries (
                            beneficiary_id, household_id, name, beneficiary_type,
                            service_code, service_name, protocol_citation, due_date,
                            is_high_risk, risk_tag, created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(beneficiary_id) DO UPDATE SET
                            name = excluded.name,
                            beneficiary_type = excluded.beneficiary_type,
                            service_code = excluded.service_code,
                            service_name = excluded.service_name,
                            protocol_citation = excluded.protocol_citation,
                            due_date = excluded.due_date,
                            is_high_risk = excluded.is_high_risk,
                            risk_tag = excluded.risk_tag,
                            updated_at = excluded.updated_at
                    """, (
                        ben_id, hh_id, rec["beneficiary_name"], rec["beneficiary_type"],
                        rec["service_code"], rec["service_name"], rec["protocol_citation"], rec["due_date"],
                        rec["is_high_risk"], rec["risk_tag"], now_iso, now_iso
                    ))
                    updated_count += 1

            conn.commit()

        return ImportReport(
            total_records=len(raw_records),
            imported_new=new_count,
            updated_existing=updated_count,
            rejected_count=len(raw_records) - (new_count + updated_count),
            errors=all_errors,
        )

    def import_from_file(self, file_path: Path) -> ImportReport:
        if not file_path.exists():
            raise FileNotFoundError(f"Register file does not exist: {file_path}")

        with open(file_path, "r", encoding="utf-8") as f:
            records = json.load(f)

        if not isinstance(records, list):
            raise ValueError("Root JSON element must be a list of household records.")

        return self.import_records(records)
