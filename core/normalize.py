"""
Text normalization and linguistic preprocessing for frontline health-worker queries.

Handles:
- Unicode normalization (NFKD), accent stripping, punctuation handling.
- Repeated letter collapsing (e.g., 'bleeeeding' -> 'bleeding', 'jwwaram' -> 'jwaram').
- Mixed-script recognition: English, Romanised Telugu/Hindi, Telugu script (0C00-0C7F), Devanagari script (0900-097F).
- Extraction of clinical numeric thresholds: Blood Pressure (BP), MUAC, Temperature, Days of Fever, Respiratory Rate.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Dict, List, Optional, Tuple


def normalize_text(text: str) -> str:
    """
    Standardize raw query string:
    - Normalizes Unicode to NFKD
    - Converts smart punctuation to ASCII
    - Strips leading/trailing spaces and collapses internal whitespace
    - Lowercases text for case-insensitive matching
    - Preserves native Indic scripts (Telugu, Devanagari) alongside Latin
    """
    if not text:
        return ""

    # NFKD decomposition
    text = unicodedata.normalize("NFKD", text)

    # Replace fancy quotes, apostrophes, and dashes
    text = text.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    text = text.replace("—", "-").replace("–", "-")

    # Lowercase
    text = text.lower()

    # Collapse repeated letters (e.g. 'bleeeed' -> 'bleed', 'soooojan' -> 'soojan')
    # Replace 3 or more repeated letters with 2
    text = re.sub(r"([a-z])\1{2,}", r"\1\1", text)

    # Collapse excessive spaces and tabs
    text = re.sub(r"\s+", " ", text).strip()
    return text


def tokenize(text: str) -> List[str]:
    """
    Tokenizes text into words preserving Latin words, Telugu script sequences,
    Devanagari script sequences, and numbers.
    """
    norm = normalize_text(text)
    # Match words in Latin, Telugu (\u0c00-\u0c7f), Devanagari (\u0900-\u097f), or numbers
    tokens = re.findall(r"[\u0c00-\u0c7fa-z0-9\u0900-\u097f]+", norm)
    return tokens


def detect_scripts(text: str) -> List[str]:
    """
    Detects which scripts are present in the text:
    'telugu', 'devanagari', 'latin'.
    """
    scripts = set()
    for ch in text:
        code = ord(ch)
        if 0x0C00 <= code <= 0x0C7F:
            scripts.add("telugu")
        elif 0x0900 <= code <= 0x097F:
            scripts.add("devanagari")
        elif ("a" <= ch.lower() <= "z"):
            scripts.add("latin")
    return sorted(list(scripts))


def extract_vitals(text: str) -> Dict[str, Optional[float | Tuple[float, float]]]:
    """
    Extracts structured clinical numbers and vital signs from raw or normalized text:
    - bp: (systolic, diastolic) or systolic alone
    - muac_mm: float in millimeters
    - temp_c: float in Celsius (converted from F if specified)
    - fever_days: integer count of days
    - respiratory_rate: breaths per minute
    """
    norm = normalize_text(text)
    vitals: Dict[str, Optional[float | Tuple[float, float]]] = {
        "bp": None,
        "muac_mm": None,
        "temp_c": None,
        "fever_days": None,
        "respiratory_rate": None,
    }

    # 1. Blood Pressure: e.g. "180/110", "140 / 90", "bp 180 110", "sys 190 dia 115", "190 by 115"
    bp_match = re.search(r"\b(?:bp|b\.p\.|blood pressure)?\s*(\d{2,3})\s*(?:[/]|by)\s*(\d{2,3})\b", norm)
    if bp_match:
        try:
            sys_val = float(bp_match.group(1))
            dia_val = float(bp_match.group(2))
            vitals["bp"] = (sys_val, dia_val)
        except ValueError:
            pass
    else:
        # Check explicit systolic/diastolic
        sys_m = re.search(r"\b(?:systolic|sys)\s*(?:is|=|:)?\s*(\d{2,3})\b", norm)
        dia_m = re.search(r"\b(?:diastolic|dia)\s*(?:is|=|:)?\s*(\d{2,3})\b", norm)
        if sys_m and dia_m:
            try:
                vitals["bp"] = (float(sys_m.group(1)), float(dia_m.group(1)))
            except ValueError:
                pass
        elif sys_m:
            try:
                vitals["bp"] = (float(sys_m.group(1)), 0.0)
            except ValueError:
                pass

    # 2. MUAC: e.g. "muac 110 mm", "muac is 11.2 cm", "muac 108", "arm circumference 11.4"
    muac_match = re.search(r"\b(?:muac|arm circumference)\s*(?:is|=|:)?\s*(\d+(?:\.\d+)?)\s*(mm|cm)?\b", norm)
    if muac_match:
        try:
            val = float(muac_match.group(1))
            unit = muac_match.group(2)
            if unit == "cm" or val < 30.0:
                # Value is in cm, convert to mm (e.g. 11.2 cm -> 112 mm)
                vitals["muac_mm"] = val * 10.0
            else:
                vitals["muac_mm"] = val
        except ValueError:
            pass

    # 3. Temperature: require explicit unit (f/c) or keyword (temp/temperature/degrees/°)
    # e.g. "103 f", "102.5 fahrenheit", "39 c", "temperature 39.5", "temp 101"
    temp_match = re.search(r"\b(?:temp|temperature)\s*(?:is|=|:)?\s*(\d{2,3}(?:\.\d+)?)\s*(?:°|deg|degrees)?\s*([fc]|fahrenheit|celsius)?\b", norm)
    if not temp_match:
        temp_match = re.search(r"\b(\d{2,3}(?:\.\d+)?)\s*(?:°|deg|degrees)\s*([fc]|fahrenheit|celsius)?\b", norm)
    if not temp_match:
        temp_match = re.search(r"\b(\d{2,3}(?:\.\d+)?)\s*([fc]|fahrenheit|celsius)\b", norm)
    if temp_match:
        try:
            val = float(temp_match.group(1))
            unit = temp_match.group(2)
            if unit in ("c", "celsius") or (val < 45.0 and val > 30.0):
                vitals["temp_c"] = val
            elif unit in ("f", "fahrenheit") or (val >= 90.0 and val <= 115.0):
                # Convert Fahrenheit to Celsius: (F - 32) * 5/9
                vitals["temp_c"] = round((val - 32.0) * 5.0 / 9.0, 1)
        except ValueError:
            pass

    # 4. Fever Days: e.g. "fever for 8 days", "fever since 10 days", "8 days fever", "2 weeks fever"
    fever_match = re.search(r"\b(?:fever|jwaram|bukhar)\s*(?:for|since|past|lasting)?\s*(\d+)\s*days\b", norm)
    if not fever_match:
        fever_match = re.search(r"\b(\d+)\s*days\s*(?:of\s*)?(?:fever|jwaram|bukhar)\b", norm)
    if not fever_match:
        # Check weeks: e.g. "2 weeks fever"
        fever_w_match = re.search(r"\b(\d+)\s*weeks?\s*(?:of\s*)?(?:fever|jwaram|bukhar)\b", norm)
        if fever_w_match:
            try:
                vitals["fever_days"] = float(fever_w_match.group(1)) * 7.0
            except ValueError:
                pass
    if fever_match:
        try:
            vitals["fever_days"] = float(fever_match.group(1))
        except ValueError:
            pass

    # 5. Respiratory Rate: e.g. "65 breaths", "respiratory rate 62", "breathing 65 per min"
    rr_match = re.search(r"\b(?:respiratory rate|breathing rate|breaths per min(?:ute)?|rr)\s*(?:is|=|:)?\s*(\d{2,3})\b", norm)
    if not rr_match:
        rr_match = re.search(r"\b(\d{2,3})\s*(?:breaths|breaths/min|breaths per minute)\b", norm)
    if rr_match:
        try:
            vitals["respiratory_rate"] = float(rr_match.group(1))
        except ValueError:
            pass

    return vitals
