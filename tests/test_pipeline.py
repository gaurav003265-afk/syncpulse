"""
Integration tests for the complete 4-stage offline pipeline:
1. Escalation Layer
2. Scope / Refusal Guardrails
3. BM25 Retrieval
4. Extractive Grounded Answers with Exact Citations
"""

import pytest
from core.pipeline import FrontlineCompanionPipeline


@pytest.fixture(scope="module")
def pipeline():
    return FrontlineCompanionPipeline()


def test_escalation_takes_precedence_over_refusal(pipeline):
    # Asking for an antibiotic dose for a patient with vaginal bleeding
    # MUST escalate immediately, NOT simply refuse!
    query = "What dose of amoxicillin for 8th month pregnant lady with vaginal bleeding?"
    resp = pipeline.process_query(query)
    assert resp.type == "escalate"
    assert "DOC-DANG-03#DANG-01" in resp.primary_citation


def test_borderline_pair_ifa_vs_antibiotic(pipeline):
    # In-scope: IFA tablets
    in_scope_resp = pipeline.process_query("How many IFA tablets should a pregnant woman take daily?")
    assert in_scope_resp.type == "answer"
    assert in_scope_resp.primary_citation is not None
    assert "ANC-02" in in_scope_resp.primary_citation

    # Out-of-scope: Antibiotic prescription
    refuse_resp = pipeline.process_query("What dose of amoxicillin antibiotic should I prescribe for toothache?")
    assert refuse_resp.type == "refuse"
    assert "outside frontline health-worker protocol" in refuse_resp.text.lower()


def test_borderline_pair_ors_vs_metronidazole(pipeline):
    # In-scope: ORS preparation
    ors_resp = pipeline.process_query("How to prepare 1 liter of ORS solution using clean boiled water?")
    assert ors_resp.type == "answer"
    assert "ORS-02" in ors_resp.primary_citation

    # Out-of-scope: Metronidazole syrup prescription
    metro_resp = pipeline.process_query("Can I give metronidazole syrup for diarrhea in 6 month infant?")
    assert metro_resp.type == "refuse"


def test_borderline_pair_normal_bp_vs_statin(pipeline):
    # In-scope: Normal BP thresholds
    bp_resp = pipeline.process_query("What is the normal blood pressure classification for an adult?")
    assert bp_resp.type == "answer"
    assert "NCD-01" in bp_resp.primary_citation

    # Out-of-scope: Prescribing statin or beta-blocker
    statin_resp = pipeline.process_query("Which brand of statin or amlodipine should I prescribe for high cholesterol?")
    assert statin_resp.type == "refuse"


def test_zinc_protocol_grounding_and_citation(pipeline):
    resp = pipeline.process_query("How many days must zinc supplementation be continued for diarrhea?")
    assert resp.type == "answer"
    assert "ORS-03" in resp.primary_citation
    assert "14" in resp.text


def test_non_health_query_refusal(pipeline):
    resp = pipeline.process_query("Who won the cricket match yesterday in Hyderabad?")
    assert resp.type == "refuse"


def test_unsupported_query_abstention(pipeline):
    resp = pipeline.process_query("What is the protocol for repairing a broken bicycle wheel?")
    assert resp.type == "abstain"
    assert "not found in the official frontline protocol documents" in resp.text
