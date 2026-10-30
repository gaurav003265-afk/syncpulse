"""
Unit and integration tests for the deterministic escalation layer.
"""

import pytest
from core.escalation import EscalationEngine
from core.normalize import extract_vitals, normalize_text


@pytest.fixture(scope="module")
def engine():
    return EscalationEngine()


def test_maternal_bleeding_english(engine):
    res = engine.check("Mother is in 3rd trimester and has severe bleeding from vagina.")
    assert res.escalate is True
    assert res.primary_rule_id == "ESC-MAT-01"
    assert "DOC-DANG-03#DANG-01" in res.corpus_citation


def test_maternal_bleeding_telugu_romanised(engine):
    res = engine.check("Garbhavathi ki raktham vasthondi sudden ga.")
    assert res.escalate is True
    assert res.primary_rule_id == "ESC-MAT-01"


def test_maternal_bleeding_telugu_native(engine):
    res = engine.check("గర్భవతికి హఠాత్తుగా రక్తస్రావం అవుతోంది.")
    assert res.escalate is True
    assert res.primary_rule_id == "ESC-MAT-01"


def test_maternal_eclampsia_fits(engine):
    res = engine.check("Pregnant lady collapsed with violent fits in village.")
    assert res.escalate is True
    assert res.primary_rule_id == "ESC-MAT-02"


def test_negation_failsafe(engine):
    # Negation must NOT suppress escalation!
    res = engine.check("Mother says she has no bleeding earlier but now there is vaginal bleeding.")
    assert res.escalate is True
    assert res.negation_detected is True
    assert res.primary_rule_id == "ESC-MAT-01"


def test_vital_signs_hypertensive_crisis(engine):
    res = engine.check("Elderly woman at home visit has BP 190/115 mmHg.")
    assert res.escalate is True
    assert res.primary_rule_id == "ESC-NCD-01"


def test_vital_signs_fast_breathing_newborn(engine):
    res = engine.check("Newborn baby has respiratory rate 66 breaths per min.")
    assert res.escalate is True
    assert res.primary_rule_id == "ESC-NEO-02"


def test_severe_malnutrition_muac(engine):
    res = engine.check("Child has MUAC 108 mm and failed appetite test.")
    assert res.escalate is True
    assert res.primary_rule_id == "ESC-NUT-02"


def test_bilateral_pitting_edema(engine):
    res = engine.check("2 year old child has bilateral pitting edema in both feet.")
    assert res.escalate is True
    assert res.primary_rule_id == "ESC-NUT-01"


def test_severe_dehydration_skin_pinch(engine):
    res = engine.check("Child with diarrhea has skin pinch going back very slowly > 2 seconds.")
    assert res.escalate is True
    assert res.primary_rule_id == "ESC-ORS-01"


def test_fever_with_stiff_neck_meningitis(engine):
    res = engine.check("Child with high fever unable to bend neck forward touch chin to chest.")
    assert res.escalate is True
    assert res.primary_rule_id == "ESC-FEV-01"


def test_routine_question_does_not_escalate(engine):
    res = engine.check("How many minimum ANC visits should a pregnant woman have?")
    assert res.escalate is False
    assert res.primary_rule_id is None


def test_routine_ors_does_not_escalate(engine):
    res = engine.check("How to prepare 1 liter of ORS solution using clean water?")
    assert res.escalate is False
    assert res.primary_rule_id is None


def test_normal_bp_does_not_escalate(engine):
    res = engine.check("What is the normal blood pressure for an adult?")
    assert res.escalate is False
    assert res.primary_rule_id is None
