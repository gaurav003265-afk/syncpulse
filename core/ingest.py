"""
Corpus ingestion and chunking module.

Parses protocol markdown documents into structured, section-tagged chunks
suitable for deterministic retrieval and exact citations.
"""

from __future__ import annotations

import os
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import List, Optional

from core.normalize import tokenize


@dataclass
class ProtocolChunk:
    chunk_id: str
    doc_id: str
    doc_title: str
    section_id: str
    section_title: str
    line_start: int
    line_end: int
    text: str
    token_count: int
    keywords: List[str]

    def to_dict(self) -> dict:
        return asdict(self)


def find_corpus_dir(custom_path: Optional[str] = None) -> Path:
    """
    Finds the active corpus directory. Prioritizes official 'data/protocols'
    if present, otherwise checks 'data/corpus' or 'data/synthetic_corpus'.
    """
    if custom_path:
        p = Path(custom_path)
        if p.exists():
            return p

    base_dir = Path(__file__).resolve().parent.parent / "data"
    official_protocols = base_dir / "protocols"
    if official_protocols.exists() and any(official_protocols.glob("*.md")):
        return official_protocols

    real_corpus = base_dir / "corpus"
    if real_corpus.exists() and any(real_corpus.glob("*.md")):
        return real_corpus

    synthetic_corpus = base_dir / "synthetic_corpus"
    if synthetic_corpus.exists():
        return synthetic_corpus

    raise FileNotFoundError(f"No corpus directory found in {base_dir}")


def ingest_corpus(corpus_dir: Optional[str] = None) -> List[ProtocolChunk]:
    """
    Reads all markdown protocol documents from the corpus directory and
    splits them into leaf section chunks (107 sections in official H5 corpus).
    Preserves exact official leaf section IDs (e.g. ANC-1.1, ESC-2.7).
    """
    c_path = find_corpus_dir(corpus_dir)
    chunks: List[ProtocolChunk] = []

    md_files = sorted(list(c_path.glob("*.md")))
    # Exclude README.md
    md_files = [f for f in md_files if f.name.lower() != "readme.md"]

    if not md_files:
        raise ValueError(f"No protocol markdown documents found in {c_path}")

    leaf_sec_re = re.compile(r"^###\s+([A-Za-z]{2,4}-\d+\.\d+)\s*(.*)")
    group_sec_re = re.compile(r"^##\s+([A-Za-z]{2,4}-\d+)\s*(.*)")
    legacy_sec_re = re.compile(r"^##\s+Section\s+([A-Za-z0-9\-]+):\s*(.+)$")
    doc_title_re = re.compile(r"^#\s+(.+)$")

    for file_path in md_files:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        doc_title = file_path.stem.replace("_", " ").title()
        doc_prefix = file_path.stem.split("_")[1] if "_" in file_path.stem else file_path.stem[:4].upper()
        doc_id = doc_prefix.upper()

        current_section_id = f"{doc_id}-0.0"
        current_section_title = "Overview & Disclaimer"
        section_lines: List[str] = []
        section_start_line = 1

        for idx, line in enumerate(lines, start=1):
            # Document Title
            dt_m = doc_title_re.match(line.strip())
            if dt_m and idx <= 5:
                doc_title = dt_m.group(1).strip()
                continue

            # Official Leaf Section (### ANC-1.1 Early registration and EDD)
            leaf_m = leaf_sec_re.match(line.strip())
            # Legacy Section (## Section ANC-01: ...)
            leg_m = legacy_sec_re.match(line.strip())

            matched_sec_id = None
            matched_sec_title = None

            if leaf_m:
                matched_sec_id = leaf_m.group(1).strip()
                matched_sec_title = leaf_m.group(2).strip() or matched_sec_id
            elif leg_m:
                matched_sec_id = leg_m.group(1).strip()
                matched_sec_title = leg_m.group(2).strip()

            if matched_sec_id:
                # Flush previous section
                if section_lines:
                    text_content = "".join(section_lines).strip()
                    if text_content and current_section_id != f"{doc_id}-0.0":
                        tokens = tokenize(text_content)
                        informative_tokens = [t for t in tokens if len(t) > 3][:25]
                        chunks.append(
                            ProtocolChunk(
                                chunk_id=current_section_id,
                                doc_id=doc_id,
                                doc_title=doc_title,
                                section_id=current_section_id,
                                section_title=current_section_title,
                                line_start=section_start_line,
                                line_end=idx - 1,
                                text=text_content,
                                token_count=len(tokens),
                                keywords=list(dict.fromkeys(informative_tokens)),
                            )
                        )
                current_section_id = matched_sec_id
                current_section_title = matched_sec_title
                section_lines = [line]
                section_start_line = idx
            else:
                section_lines.append(line)

        # Flush final section
        if section_lines:
            text_content = "".join(section_lines).strip()
            if text_content and current_section_id != f"{doc_id}-0.0":
                tokens = tokenize(text_content)
                informative_tokens = [t for t in tokens if len(t) > 3][:25]
                chunks.append(
                    ProtocolChunk(
                        chunk_id=current_section_id,
                        doc_id=doc_id,
                        doc_title=doc_title,
                        section_id=current_section_id,
                        section_title=current_section_title,
                        line_start=section_start_line,
                        line_end=len(lines),
                        text=text_content,
                        token_count=len(tokens),
                        keywords=list(dict.fromkeys(informative_tokens)),
                    )
                )

    return chunks


if __name__ == "__main__":
    import sys
    if sys.stdout.encoding != "utf-8":
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass
    chunks = ingest_corpus()
    print(f"Successfully ingested {len(chunks)} chunks from corpus:")
    for c in chunks:
        print(f" - [{c.doc_id}] {c.section_id}: {c.section_title} ({c.token_count} tokens, lines {c.line_start}-{c.line_end})")
