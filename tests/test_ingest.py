"""
Unit tests for corpus ingestion and knowledge pack generation.
"""

import json
from pathlib import Path
from core.ingest import ingest_corpus
from core.build_pack import build_knowledge_pack


def test_ingest_all_protocol_sections():
    chunks = ingest_corpus()
    assert len(chunks) >= 30

    section_ids = {c.section_id for c in chunks}
    # Verify key clinical sections exist
    expected_sections = [
        "ANC-1.1", "ANC-2.1", "ANC-3.1",
        "IMM-1.1", "IMM-2.1", "IMM-2.3",
        "ESC-1.1", "ESC-2.1", "ESC-2.2", "ESC-6.1",
        "NUT-1.1", "NUT-1.2",
        "NCD-1.1", "NCD-1.2", "NCD-2.1",
        "CHD-1.1", "CHD-1.2", "CHD-2.1", "CHD-3.1",
        "VIS-1.1", "VIS-2.1"
    ]
    for sec in expected_sections:
        assert sec in section_ids, f"Section {sec} missing from ingested chunks"


def test_chunk_attributes_and_citations():
    chunks = ingest_corpus()
    for c in chunks:
        assert c.chunk_id
        assert c.line_start <= c.line_end
        assert len(c.text.strip()) > 0
        assert c.token_count > 0


def test_knowledge_pack_manifest_and_bm25(tmp_path):
    pack_dir = build_knowledge_pack(output_dir=str(tmp_path / "test_pack"))
    manifest_file = pack_dir / "manifest.json"
    chunks_file = pack_dir / "chunks.json"
    bm25_file = pack_dir / "bm25_index.json"

    assert manifest_file.exists()
    assert chunks_file.exists()
    assert bm25_file.exists()

    with open(manifest_file, "r", encoding="utf-8") as f:
        manifest = json.load(f)
        assert manifest["pack_version"] == "1.0.0"
        assert manifest["total_documents"] == 9
        assert len(manifest["document_hashes"]) == 9

    with open(bm25_file, "r", encoding="utf-8") as f:
        bm25 = json.load(f)
        assert "inverted_index" in bm25
        assert len(bm25["inverted_index"]) > 500
