"""
Knowledge pack build script.

Packages the corpus documents, section-tagged chunks, BM25 inverted index,
and escalation rules into a versioned, portable knowledge pack for offline use.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from core.ingest import find_corpus_dir, ingest_corpus
from core.normalize import tokenize


def calculate_sha256(file_path: Path) -> str:
    """Computes SHA-256 hexadecimal hash of a file."""
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def build_bm25_index(chunks: List[Any]) -> Dict[str, Any]:
    """
    Builds a precomputed BM25 inverted index for rapid offline scoring:
    - doc_len: list of token lengths for each chunk
    - avg_dl: average chunk token length
    - inverted_index: token -> [[chunk_idx, term_freq], ...]
    - doc_count: total chunks
    """
    doc_lens = []
    inverted_index: Dict[str, List[List[int]]] = {}

    for idx, c in enumerate(chunks):
        # Index tokens from section title, doc title, keywords, and text
        tokens = tokenize(f"{c.doc_title} {c.section_title} {' '.join(c.keywords)} {c.text}")
        doc_lens.append(len(tokens))

        tf = Counter(tokens)
        for tok, count in tf.items():
            if tok not in inverted_index:
                inverted_index[tok] = []
            inverted_index[tok].append([idx, count])

    avg_dl = sum(doc_lens) / max(1, len(doc_lens))

    return {
        "k1": 1.5,
        "b": 0.75,
        "doc_count": len(chunks),
        "avg_dl": round(avg_dl, 2),
        "doc_lens": doc_lens,
        "inverted_index": inverted_index,
    }


def build_knowledge_pack(output_dir: Optional[str] = None) -> Path:
    """
    Builds the full knowledge pack and saves it to data/knowledge_pack/.
    """
    root_dir = Path(__file__).resolve().parent.parent
    if output_dir is None:
        out_path = root_dir / "data" / "knowledge_pack"
    else:
        out_path = Path(output_dir)

    out_path.mkdir(parents=True, exist_ok=True)

    # 1. Ingest chunks
    chunks = ingest_corpus()
    chunk_dicts = [c.to_dict() for c in chunks]

    # 2. Build BM25 index
    bm25_data = build_bm25_index(chunks)

    # 3. Hash corpus files and rules
    corpus_dir = find_corpus_dir()
    corpus_hashes: Dict[str, str] = {}
    for f in sorted(list(corpus_dir.glob("*.md"))):
        if f.name.lower() != "readme.md":
            corpus_hashes[f.name] = calculate_sha256(f)

    rules_path = root_dir / "data" / "escalation_rules.json"
    rules_hash = calculate_sha256(rules_path) if rules_path.exists() else ""

    # 4. Create Manifest
    manifest = {
        "pack_version": "1.0.0",
        "pack_name": "ASHA_ANM_CLINICAL_PROTOCOLS_AP_2026",
        "build_timestamp": datetime.now(timezone.utc).isoformat(),
        "total_documents": len(corpus_hashes),
        "total_chunks": len(chunks),
        "total_tokens": sum(c.token_count for c in chunks),
        "languages": ["en", "te", "hi", "romanized_telugu", "romanized_hindi"],
        "corpus_directory": corpus_dir.name,
        "document_hashes": corpus_hashes,
        "escalation_rules_hash": rules_hash,
    }

    # 5. Write artifacts
    with open(out_path / "manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    with open(out_path / "chunks.json", "w", encoding="utf-8") as f:
        json.dump(chunk_dicts, f, indent=2, ensure_ascii=False)

    with open(out_path / "bm25_index.json", "w", encoding="utf-8") as f:
        json.dump(bm25_data, f, ensure_ascii=False)

    # Copy rules into pack
    if rules_path.exists():
        with open(rules_path, "r", encoding="utf-8") as rf, open(out_path / "escalation_rules.json", "w", encoding="utf-8") as wf:
            wf.write(rf.read())

    print(f"Knowledge Pack v{manifest['pack_version']} successfully built at: {out_path}")
    print(f" - Documents: {manifest['total_documents']}")
    print(f" - Chunks: {manifest['total_chunks']}")
    print(f" - Unique BM25 indexed tokens: {len(bm25_data['inverted_index'])}")
    print(f" - Manifest SHA-256 records verified: {len(corpus_hashes)} files")

    return out_path


if __name__ == "__main__":
    build_knowledge_pack()
