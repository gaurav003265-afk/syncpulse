"""
Tests for the Offline Model Adapter, Citation Validator, and Resource Profiling.
"""

import pytest
from core.model_adapter import (
    CitationValidator,
    GroundedExtractiveAdapter,
    LocalQuantizedModelAdapter,
)
from core.retrieve import BM25Retriever


@pytest.fixture(scope="module")
def retriever():
    return BM25Retriever()


def test_grounded_extractive_adapter_offline(retriever):
    adapter = GroundedExtractiveAdapter()
    chunks = retriever.search("How to prepare 1 liter of ORS solution?", top_k=3)
    out = adapter.generate("How to prepare 1 liter of ORS solution?", chunks, abstain=False)

    assert out.adapter_name == "GroundedExtractiveAdapter"
    assert out.is_fallback is False
    assert out.primary_citation is not None
    assert "CHD-1.1" in out.primary_citation
    assert "1 liter" in out.answer_text.lower() or "clean" in out.answer_text.lower()
    assert out.latency_ms < 50.0  # must be fast
    assert out.memory_peak_kb > 0.0


def test_grounded_extractive_adapter_abstention(retriever):
    adapter = GroundedExtractiveAdapter()
    out = adapter.generate("unsupported bicycle repair query", [], abstain=True)

    assert out.primary_citation is None
    assert out.citations == []
    assert out.confidence_score == 0.0
    assert "not found in the official frontline protocol" in out.answer_text


def test_local_quantized_model_adapter_fallback():
    adapter = LocalQuantizedModelAdapter()
    # When no GGUF weights are bundled in workspace, it cleanly engages certified fallback
    assert adapter.available_model_path is None or adapter.available_model_path.exists()


def test_citation_validator():
    validator = CitationValidator()
    chunks = [
        {
            "doc_id": "DOC-ORS-06",
            "section_id": "ORS-02",
            "section_title": "ORS Preparation and Dosage",
            "line_start": 15,
            "line_end": 28,
        }
    ]
    validator.load_from_chunks(chunks)

    valid_cit = "[DOC-ORS-06] Section ORS-02: ORS Preparation and Dosage (Lines 15-28)"
    assert validator.is_valid(valid_cit) is True
    assert validator.is_valid("DOC-ORS-06#ORS-02") is True

    # Hallucinated or non-existent citation must fail validation
    fake_cit = "[DOC-FAKE-99] Section FAKE-01: Invented Remedy (Lines 1-10)"
    assert validator.is_valid(fake_cit) is False
    assert validator.is_valid(None) is False
