"""
Unit tests for Speech Processing, Transcript Validation, and Silence/Noise Handling.
"""

import pytest
from core.speech import validate_transcript


def test_silence_empty_input():
    res = validate_transcript("")
    assert res.is_understandable is False
    assert res.status == "silence"

    res_spaces = validate_transcript("    \t\n  ")
    assert res_spaces.is_understandable is False
    assert res_spaces.status == "silence"


def test_conversational_filler_noise():
    noisy = "uh well um the thing with the thing yes yesterday"
    res = validate_transcript(noisy)
    assert res.is_understandable is False
    assert res.status == "noisy_unclear"
    assert "Speech was unclear" in res.message


def test_emergency_voice_queries():
    # English emergency
    res_en = validate_transcript("Seven months pregnant woman heavy bleeding from vagina")
    assert res_en.is_understandable is True
    assert res_en.status == "valid"

    # Telugu code-mix emergency
    res_te = validate_transcript("Garbhavathi ki fits vachayi sudden ga")
    assert res_te.is_understandable is True
    assert res_te.status == "valid"

    # Hindi code-mix emergency
    res_hi = validate_transcript("Navjat shishu ki saans tez chal rahi hai rr 64")
    assert res_hi.is_understandable is True
    assert res_hi.status == "valid"


def test_routine_voice_queries():
    res_ors = validate_transcript("How to prepare one liter of ORS solution for child diarrhea")
    assert res_ors.is_understandable is True
    assert res_ors.status == "valid"

    res_tika = validate_transcript("Pillalaki pentavalent tika eppudu ivvali")
    assert res_tika.is_understandable is True
    assert res_tika.status == "valid"


def test_transcript_validation_to_dict_and_typing():
    res = validate_transcript("Seven months pregnant woman heavy bleeding")
    d = res.to_dict()
    assert isinstance(d, dict)
    assert d["is_understandable"] is True
    assert d["status"] == "valid"

