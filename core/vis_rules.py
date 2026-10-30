"""
Official VIS Daily Visit List Rules Engine (09_VIS_daily_visit_list_rules.md).
Generates official member-level due items and priorities for the Chandrapuri Block.

Fixed benchmark date: 2026-10-26 (Monday).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import pandas as pd

TODAY = date(2026, 10, 26)

ANC_WINDOWS = {
    1: (0, 84),      # ANC-1: opens 0, closes 84
    2: (98, 182),    # ANC-2: opens 98, closes 182
    3: (196, 238),   # ANC-3: opens 196, closes 238
    4: (252, 280),   # ANC-4: opens 252, closes 280
}

# Vaccine table from VIS-3.1
# (Item, due_age_days, not_after_days, prev_dose_needed, min_gap_days)
VACCINE_TABLE = [
    ("BCG", 0, 365, None, None),
    ("HepB-0", 0, 0, None, None),
    ("OPV-0", 0, 15, None, None),
    ("OPV-1", 42, 1825, None, None),
    ("OPV-2", 70, 1825, "OPV-1", 28),
    ("OPV-3", 98, 1825, "OPV-2", 28),
    ("Penta-1", 42, 365, None, None),
    ("Penta-2", 70, 365, "Penta-1", 28),
    ("Penta-3", 98, 365, "Penta-2", 28),
    ("RVV-1", 42, 365, None, None),
    ("RVV-2", 70, 365, "RVV-1", 28),
    ("RVV-3", 98, 365, "RVV-2", 28),
    ("fIPV-1", 42, 365, None, None),
    ("fIPV-2", 98, 365, "fIPV-1", 56),
    ("fIPV-3", 276, 729, "fIPV-2", 56),
    ("PCV-1", 42, 365, None, None),
    ("PCV-2", 98, 729, "PCV-1", 60),
    ("PCV-B", 276, 729, "PCV-2", 60),
    ("MR-1", 276, 1825, None, None),
    ("MR-2", 490, 1825, "MR-1", 28),
    ("OPV-B", 490, 1825, "OPV-3", 180),
    ("DPT-B1", 490, 2554, "Penta-3", 180),
    ("DPT-B2", 1827, 2554, "DPT-B1", None),
]

HBNC_SCHEDULE = {
    "institution": [3, 7, 14, 21, 28, 42],
    "home": [1, 3, 7, 14, 21, 28, 42],
}


def parse_date(val: Any) -> Optional[date]:
    if not val or pd.isna(val):
        return None
    s = str(val).strip()
    if not s:
        return None
    try:
        return date.fromisoformat(s)
    except Exception:
        return None


def parse_bp(val: Any) -> Tuple[Optional[int], Optional[int]]:
    if not val or pd.isna(val):
        return None, None
    m = re.match(r"^(\d+)\s*/\s*(\d+)$", str(val).strip())
    if m:
        sys_bp, dia_bp = int(m.group(1)), int(m.group(2))
        if sys_bp == 0 and dia_bp == 0:
            return None, None
        return sys_bp, dia_bp
    return None, None


def normalize_vaccine_code(raw_code: str) -> str:
    c = str(raw_code).strip().upper()
    c = re.sub(r"[\s\-_]+", "", c)
    mapping = {
        "BCG": "BCG",
        "HEPB0": "HepB-0", "HEPB": "HepB-0",
        "OPV0": "OPV-0", "OPV1": "OPV-1", "OPV2": "OPV-2", "OPV3": "OPV-3", "OPVB": "OPV-B",
        "PENTA1": "Penta-1", "PENTA2": "Penta-2", "PENTA3": "Penta-3",
        "RVV1": "RVV-1", "RVV2": "RVV-2", "RVV3": "RVV-3",
        "FIPV1": "fIPV-1", "FIPV2": "fIPV-2", "FIPV3": "fIPV-3",
        "PCV1": "PCV-1", "PCV2": "PCV-2", "PCVB": "PCV-B",
        "MR1": "MR-1", "MR2": "MR-2",
        "DPTB1": "DPT-B1", "DPTB2": "DPT-B2",
    }
    return mapping.get(c, str(raw_code).strip())


def parse_child_vaccines(cell_value: str) -> Dict[str, date]:
    """Parses vaccines received by child, returning map of normalized_code -> earliest_date."""
    received: Dict[str, date] = {}
    if not cell_value or pd.isna(cell_value):
        return received
    for item in str(cell_value).split(";"):
        item = item.strip()
        if not item or ":" not in item:
            continue
        parts = item.split(":", 1)
        code = normalize_vaccine_code(parts[0])
        dt = parse_date(parts[1])
        if dt:
            if code not in received or dt < received[code]:
                received[code] = dt
    return received


def is_member_high_risk(r: pd.Series, today: date = TODAY) -> bool:
    """
    Evaluates whether a member meets official VIS-5.1 high-risk criteria:
    - Pregnant woman: Hb < 7 g/dL OR last ANC BP >= 140/90.
    - Baby: age <= 42 days.
    - Child 184-1824 days: last MUAC < 11.5 cm OR bilateral_pitting_oedema == 'Y'.
    - NCD patient: last recorded BP >= 140/90.
    """
    dob = parse_date(r.get("dob"))
    age_days = (today - dob).days if dob else 99999

    # 1. Pregnant woman
    if str(r.get("pregnant", "")).strip().upper() == "Y":
        # Check Hb
        hb_str = str(r.get("last_hb_gdl", "")).strip()
        if hb_str:
            try:
                hb = float(hb_str)
                if hb < 7.0:
                    return True
            except ValueError:
                pass
        # Check ANC BP
        sys_bp, dia_bp = parse_bp(r.get("last_anc_bp"))
        if sys_bp is not None and dia_bp is not None:
            if sys_bp >= 140 or dia_bp >= 90:
                return True

    # 2. Newborn <= 42 days
    if age_days <= 42:
        return True

    # 3. Child 184-1824 days
    if 184 <= age_days <= 1824:
        muac_str = str(r.get("last_muac_cm", "")).strip()
        if muac_str:
            try:
                muac = float(muac_str)
                if muac < 11.5:
                    return True
            except ValueError:
                pass
        if str(r.get("bilateral_pitting_oedema", "")).strip().upper() == "Y":
            return True

    # 4. NCD patient
    ncd = str(r.get("ncd_condition", "")).strip().upper()
    if any(k in ncd for k in ("HTN", "DM")):
        sys_bp, dia_bp = parse_bp(r.get("last_bp_reading"))
        if sys_bp is not None and dia_bp is not None:
            if sys_bp >= 140 or dia_bp >= 90:
                return True

    return False


def calculate_member_due_items(
    r: pd.Series, today: date = TODAY
) -> List[Tuple[str, str, int, str, Optional[date]]]:
    """
    Generates all due items for a single member according to VIS rules.
    Returns list of tuples: (member_id, due_item, priority, status, due_date)
    """
    member_id = str(r["member_id"]).strip()
    is_hr = is_member_high_risk(r, today)
    dob = parse_date(r.get("dob"))
    age_days = (today - dob).days if dob else 99999

    items: List[Tuple[str, str, int, str, Optional[date]]] = []

    def add_item(code: str, due_dt: date, late_after: date):
        """Helper to determine status, priority, and horizon filter."""
        if due_dt > today + timedelta(days=6):
            return  # Beyond horizon
        if due_dt > today:
            status = "due_this_week"
            priority = 3
        elif today <= late_after:
            status = "due_today"
            priority = 1 if is_hr else 2
        else:
            status = "overdue"
            priority = 1 if is_hr else 2
        items.append((member_id, code, priority, status, due_dt))

    # =========================================================================
    # VIS-2: PREGNANT WOMEN
    # =========================================================================
    if str(r.get("pregnant", "")).strip().upper() == "Y":
        lmp = parse_date(r.get("lmp_date"))
        if lmp:
            # 1. ANC Check-ups (VIS-2.1)
            raw_anc = str(r.get("anc_visit_dates", "")).strip()
            done_anc = [x.strip() for x in raw_anc.split(";") if x.strip()]
            k = len(done_anc) + 1
            if k <= 4:
                opens, closes = ANC_WINDOWS[k]
                anc_due = lmp + timedelta(days=opens)
                anc_close = lmp + timedelta(days=closes)
                if anc_due <= today + timedelta(days=6):
                    if anc_due > today:
                        items.append((member_id, f"ANC-{k}", 3, "due_this_week", anc_due))
                    elif today <= anc_close:
                        items.append((member_id, f"ANC-{k}", 1 if is_hr else 2, "due_today", anc_due))
                    else:
                        items.append((member_id, f"ANC-{k}", 1 if is_hr else 2, "overdue", anc_due))

            # 2. Td in pregnancy (VIS-2.2)
            td_booster = str(r.get("td_booster_eligible", "")).strip().upper() == "Y"
            raw_td = str(r.get("td_doses", "")).strip()
            td_doses: Dict[str, date] = {}
            for item in raw_td.split(";"):
                if ":" in item:
                    p = item.split(":", 1)
                    p_code = p[0].strip().upper().replace(" ", "").replace("_", "-")
                    p_dt = parse_date(p[1])
                    if p_dt:
                        td_doses[p_code] = p_dt

            # First ANC date (Td requires at least 1 recorded ANC check-up)
            first_anc_dt = parse_date(done_anc[0]) if done_anc else None
            if first_anc_dt:
                if td_booster:
                    # Needs Td-BST
                    if "TD-BST" not in td_doses and "TD1" not in td_doses and "TD-1" not in td_doses:
                        add_item("Td-BST", first_anc_dt, first_anc_dt + timedelta(days=28))
                else:
                    # Needs Td-1 and Td-2
                    has_td1 = any(k in td_doses for k in ("TD-1", "TD1"))
                    has_td2 = any(k in td_doses for k in ("TD-2", "TD2"))
                    if not has_td1:
                        add_item("Td-1", first_anc_dt, first_anc_dt + timedelta(days=28))
                    elif not has_td2:
                        td1_dt = td_doses.get("TD-1") or td_doses.get("TD1")
                        if td1_dt:
                            td2_due = td1_dt + timedelta(days=28)
                            add_item("Td-2", td2_due, td2_due + timedelta(days=28))

        # 3. High-Risk Pregnancy Follow-Up (VIS-2.3)
        # Every pregnant woman whose last Hb < 7 or ANC BP >= 140/90 gets HRP-followup
        hb_val = None
        try:
            if str(r.get("last_hb_gdl", "")).strip():
                hb_val = float(str(r.get("last_hb_gdl", "")).strip())
        except ValueError:
            pass
        sys_bp, dia_bp = parse_bp(r.get("last_anc_bp"))
        is_hrp = (hb_val is not None and hb_val < 7.0) or (
            sys_bp is not None and dia_bp is not None and (sys_bp >= 140 or dia_bp >= 90)
        )
        if is_hrp:
            items.append((member_id, "HRP-followup", 1, "due_today", today))

    # =========================================================================
    # VIS-4: NEWBORNS (Age <= 42 days)
    # =========================================================================
    if dob and age_days <= 42:
        place = str(r.get("place_of_delivery", "institution")).strip().lower()
        if place not in HBNC_SCHEDULE:
            place = "institution"
        sched = HBNC_SCHEDULE[place]

        raw_hbnc = str(r.get("hbnc_visits_done", "")).strip()
        done_days = set()
        for x in raw_hbnc.split(";"):
            x = x.strip()
            if x.isdigit():
                done_days.add(int(x))

        # Rule: take the latest scheduled visit dated on or before today
        past_or_today_visits = [d for d in sched if (dob + timedelta(days=d - 1)) <= today]
        future_visits = [d for d in sched if (dob + timedelta(days=d - 1)) > today]

        hbnc_item_added = False
        if past_or_today_visits:
            latest_d = past_or_today_visits[-1]
            if latest_d not in done_days:
                v_dt = dob + timedelta(days=latest_d - 1)
                st = "due_today" if v_dt == today else "overdue"
                items.append((member_id, f"HBNC-D{latest_d}", 1, st, v_dt))
                hbnc_item_added = True

        if not hbnc_item_added and future_visits:
            next_d = future_visits[0]
            if next_d not in done_days:
                v_dt = dob + timedelta(days=next_d - 1)
                if v_dt <= today + timedelta(days=6):
                    items.append((member_id, f"HBNC-D{next_d}", 3, "due_this_week", v_dt))

    # =========================================================================
    # VIS-3: CHILDREN VACCINES (Age <= 2554 days)
    # =========================================================================
    if dob and age_days <= 2554:
        received_vac = parse_child_vaccines(str(r.get("child_vaccines", "")))

        for v_code, due_age, not_after, prev_needed, min_gap in VACCINE_TABLE:
            if v_code in received_vac:
                continue
            if prev_needed and prev_needed not in received_vac:
                continue
            if not_after is not None and age_days > not_after:
                continue

            # Calculate due date
            due_from_age = dob + timedelta(days=due_age)
            if prev_needed and min_gap:
                prev_date = received_vac[prev_needed]
                due_dt = max(due_from_age, prev_date + timedelta(days=min_gap))
            else:
                due_dt = due_from_age

            # If due date exceeds not_after, dose cannot be listed
            if not_after is not None:
                not_after_dt = dob + timedelta(days=not_after)
                if due_dt > not_after_dt:
                    continue
                late_after = min(due_dt + timedelta(days=28), not_after_dt)
            else:
                late_after = due_dt + timedelta(days=28)

            add_item(v_code, due_dt, late_after)

    # =========================================================================
    # VIS-5.2: MUAC CHECK (Children 6 to 59 months: 178 to 1824 days)
    # =========================================================================
    if dob and 178 <= age_days <= 1824:
        last_muac_dt = parse_date(r.get("last_muac_date"))
        if last_muac_dt:
            muac_due = last_muac_dt + timedelta(days=30)
        else:
            muac_due = dob + timedelta(days=184)
        add_item("MUAC-check", muac_due, muac_due + timedelta(days=28))

    # =========================================================================
    # VIS-5.3: NCD FOLLOW-UP (HTN and DM)
    # =========================================================================
    ncd_cond = str(r.get("ncd_condition", "")).strip().upper()
    if "HTN" in ncd_cond:
        last_bp_dt = parse_date(r.get("last_bp_check_date"))
        if last_bp_dt:
            bp_due = last_bp_dt + timedelta(days=30)
            add_item("BP-followup", bp_due, bp_due + timedelta(days=28))
        else:
            items.append((member_id, "BP-followup", 1 if is_hr else 2, "overdue", None))

    if "DM" in ncd_cond:
        last_sug_dt = parse_date(r.get("last_sugar_check_date"))
        if last_sug_dt:
            sug_due = last_sug_dt + timedelta(days=30)
            add_item("Sugar-followup", sug_due, sug_due + timedelta(days=28))
        else:
            items.append((member_id, "Sugar-followup", 1 if is_hr else 2, "overdue", None))

    return items


def generate_whole_register_visit_list(
    register_csv_path: Optional[str] = None,
    today: date = TODAY,
) -> pd.DataFrame:
    """
    Generates the complete whole-register visit list matching the official submission schema:
    Columns: member_id, due_item, priority
    """
    if register_csv_path is None:
        p = Path(__file__).resolve().parent.parent / "data" / "official" / "household_register.csv"
        if not p.exists():
            p = Path(__file__).resolve().parent.parent / "official_dataset" / "data" / "household_register.csv"
    else:
        p = Path(register_csv_path)

    df = pd.read_csv(p, dtype=str, keep_default_na=False)

    rows: List[Dict[str, Any]] = []
    for _, r in df.iterrows():
        items = calculate_member_due_items(r, today=today)
        for mem_id, item_code, prio, status_label, due_dt in items:
            rows.append({
                "member_id": mem_id,
                "due_item": item_code,
                "priority": prio,
                "status": status_label,
                "due_date": due_dt.isoformat() if due_dt else None,
            })

    out_df = pd.DataFrame(rows)
    if not out_df.empty:
        # Drop accidental duplicate (member_id, due_item) pairs
        out_df = out_df.drop_duplicates(subset=["member_id", "due_item"])
    return out_df
