"""
Synthetic 500-household register generator.

Follows official NHM / ASHA village register format:
- Pregnant mothers (ANC visits 1-4, Td, IFA, high-risk flags)
- Infants & Children (NIS vaccination milestones, MUAC malnutrition screening)
- Chronic Disease Adults (Hypertension BP, Diabetes blood glucose follow-up)
- Zero real patient data: strictly synthetic stand-in for hackathon prototyping.
"""

from __future__ import annotations

import json
import random
from datetime import date, timedelta
from pathlib import Path


def generate_households(count: int = 500, anchor_date: date = date(2026, 10, 20)) -> Path:
    random.seed(2026)

    villages = ["Venkatapuram", "Kothur", "Anantharam", "Mamidipally", "Ramnagar"]
    family_names = [
        "Reddy", "Rao", "Naidu", "Varma", "Goud", "Kumar", "Chowdary",
        "Murthy", "Babu", "Sharma", "Devi", "Prasad", "Raju", "Lakshmi"
    ]

    services_catalog = [
        # Maternal (ANC)
        {
            "type": "Maternal",
            "code": "ANC_VISIT_1",
            "name": "First ANC Checkup (Early Registration & MCP Card)",
            "citation": "[DOC-ANC-01] Section ANC-01",
        },
        {
            "type": "Maternal",
            "code": "ANC_VISIT_2",
            "name": "Second ANC Checkup (14-26 Weeks) + IFA Initiation",
            "citation": "[DOC-ANC-01] Section ANC-01",
        },
        {
            "type": "Maternal",
            "code": "ANC_VISIT_3",
            "name": "Third ANC Checkup (28-34 Weeks) + Fetal Assessment",
            "citation": "[DOC-ANC-01] Section ANC-01",
        },
        {
            "type": "Maternal",
            "code": "ANC_VISIT_4",
            "name": "Fourth ANC Checkup (36+ Weeks - Birth Plan & FRU)",
            "citation": "[DOC-ANC-01] Section ANC-01",
        },
        {
            "type": "Maternal",
            "code": "TD_BOOSTER",
            "name": "Td Booster Injection for Pregnant Mother",
            "citation": "[DOC-ANC-01] Section ANC-02",
        },
        # Immunisation (Infant / Child)
        {
            "type": "Infant",
            "code": "IMM_BIRTH",
            "name": "Birth Dose (BCG + OPV-0 + Hepatitis B)",
            "citation": "[DOC-IMM-02] Section IMM-01",
        },
        {
            "type": "Infant",
            "code": "IMM_6_WEEKS",
            "name": "Primary 6-Week Vaccines (Pentavalent-1 + OPV-1 + RVV-1 + fIPV-1)",
            "citation": "[DOC-IMM-02] Section IMM-02",
        },
        {
            "type": "Infant",
            "code": "IMM_10_WEEKS",
            "name": "Primary 10-Week Vaccines (Pentavalent-2 + OPV-2 + RVV-2)",
            "citation": "[DOC-IMM-02] Section IMM-02",
        },
        {
            "type": "Infant",
            "code": "IMM_14_WEEKS",
            "name": "Primary 14-Week Vaccines (Pentavalent-3 + OPV-3 + RVV-3 + fIPV-2)",
            "citation": "[DOC-IMM-02] Section IMM-02",
        },
        {
            "type": "Infant",
            "code": "IMM_9_MONTHS",
            "name": "Measles-Rubella MR-1 + Vitamin A 1st Dose (9 Months)",
            "citation": "[DOC-IMM-02] Section IMM-03",
        },
        {
            "type": "Child",
            "code": "IMM_16_MONTHS",
            "name": "DPT Booster-1 + MR-2 + OPV Booster (16-24 Months)",
            "citation": "[DOC-IMM-02] Section IMM-04",
        },
        # Nutrition
        {
            "type": "Child",
            "code": "NUT_MUAC_SCREEN",
            "name": "Quarterly MUAC Tape Malnutrition Rescreening",
            "citation": "[DOC-NUT-04] Section NUT-01",
        },
        # NCD
        {
            "type": "Adult_NCD",
            "code": "NCD_BP_CHECK",
            "name": "Monthly Hypertension Blood Pressure Follow-up",
            "citation": "[DOC-NCD-05] Section NCD-01",
        },
        {
            "type": "Adult_NCD",
            "code": "NCD_SUGAR_CHECK",
            "name": "Monthly Diabetes Capillary Blood Glucose Monitoring",
            "citation": "[DOC-NCD-05] Section NCD-03",
        },
    ]

    households = []

    for i in range(1, count + 1):
        hh_id = f"HH-{i:04d}"
        village = random.choice(villages)
        fam = random.choice(family_names)
        head_name = f"{fam} {random.choice(['Suresh', 'Ramesh', 'Venkatesh', 'Narayana', 'Srinivas', 'Anjaneyulu'])}"
        contact = f"98{random.randint(10000000, 99999999)}"

        serv = random.choice(services_catalog)
        b_type = serv["type"]
        if b_type == "Maternal":
            b_name = f"{random.choice(['Lakshmi', 'Sunitha', 'Swapna', 'Padma', 'Kavitha', 'Lavanya', 'Anitha'])} {fam}"
        elif b_type in ("Infant", "Child"):
            b_name = f"Child of {random.choice(['Bhavani', 'Sirisha', 'Radha', 'Kalyani'])} {fam}"
        else:
            b_name = f"{random.choice(['Ramana', 'Krishna', 'Apparao', 'Satyanarayana', 'Govind'])} {fam}"

        # Assign high-risk flag to ~14% of families
        is_high_risk = (i % 7 == 0)
        risk_tag = None
        if is_high_risk:
            if b_type == "Maternal":
                risk_tag = random.choice([
                    "High BP history (Pre-eclampsia risk)",
                    "Severe anemia (Hb < 7 g/dL)",
                    "Twin pregnancy / High-risk maternal age",
                    "Previous Cesarean section delivery"
                ])
            elif b_type in ("Infant", "Child"):
                risk_tag = random.choice([
                    "Low birth weight (< 2.0 kg)",
                    "Previous Severe Acute Malnutrition (SAM history)",
                    "Preterm delivery (34 weeks)"
                ])
            else:
                risk_tag = random.choice([
                    "Stage 2 Hypertension (BP > 160/100)",
                    "Uncontrolled Diabetes (FBS > 200 mg/dL)",
                    "History of TIA / Stroke"
                ])

        # Distribute due dates around anchor_date:
        # - 25% Critically Overdue (-21 to -8 days)
        # - 35% Overdue (-7 to -1 days)
        # - 15% Due Today (0 days)
        # - 25% Upcoming (+1 to +10 days)
        roll = random.random()
        if roll < 0.25:
            offset = random.randint(-21, -8)
        elif roll < 0.60:
            offset = random.randint(-7, -1)
        elif roll < 0.75:
            offset = 0
        else:
            offset = random.randint(1, 10)

        due_d = anchor_date + timedelta(days=offset)

        households.append({
            "household_id": hh_id,
            "village": village,
            "household_head": head_name,
            "contact_phone": contact,
            "beneficiary_name": b_name,
            "beneficiary_type": b_type,
            "service_code": serv["code"],
            "service_name": serv["name"],
            "protocol_citation": serv["citation"],
            "due_date": due_d.isoformat(),
            "is_high_risk": is_high_risk,
            "risk_tag": risk_tag,
            "visited": False,
            "visited_at": None,
            "visit_notes": None,
        })

    out_file = Path(__file__).resolve().parent / "households.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(households, f, indent=2, ensure_ascii=False)

    print(f"Generated {len(households)} synthetic households in {out_file}:")
    print(f" - Anchor Date  : {anchor_date}")
    print(f" - High-Risk    : {sum(1 for h in households if h['is_high_risk'])}")
    print(f" - Overdue (< 0): {sum(1 for h in households if h['due_date'] < anchor_date.isoformat())}")
    print(f" - Due Today (0): {sum(1 for h in households if h['due_date'] == anchor_date.isoformat())}")
    print(f" - Upcoming (> 0): {sum(1 for h in households if h['due_date'] > anchor_date.isoformat())}")
    return out_file


if __name__ == "__main__":
    generate_households()
