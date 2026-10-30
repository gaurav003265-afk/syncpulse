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
    Finds the active corpus directory. Prioritizes organizer-provided 'data/corpus'
    if present, otherwise falls back to clearly labelled 'data/synthetic_corpus'.
    """
    if custom_path:
        p = Path(custom_path)
        if p.exists():
            return p

    base_dir = Path(__file__).resolve().parent.parent / "data"
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
    splits them into section-tagged chunks.
    """
    c_path = find_corpus_dir(corpus_dir)
    chunks: List[ProtocolChunk] = []

    md_files = sorted(list(c_path.glob("*.md")))
    # Exclude README.md
    md_files = [f for f in md_files if f.name.lower() != "readme.md"]

    if not md_files:
        raise ValueError(f"No protocol markdown documents found in {c_path}")

    for file_path in md_files:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        doc_title = file_path.stem.replace("_", " ").title()
        doc_id = f"DOC-{file_path.stem[:6].upper()}"

        current_section_id = "GEN-01"
        current_section_title = "General Overview"
        section_lines: List[str] = []
        section_start_line = 1

        for idx, line in enumerate(lines, start=1):
            # Check for Document ID line: "Document ID: DOC-ANC-01"
            doc_id_match = re.match(r"^Document ID:\s*([A-Za-z0-9\-]+)", line.strip(), re.IGNORECASE)
            if doc_id_match:
                doc_id = doc_id_match.group(1).strip()
                continue

            # Check for Doc Title: "# Protocol 01: ..."
            doc_title_match = re.match(r"^#\s+(.+)$", line.strip())
            if doc_title_match and idx <= 5:
                doc_title = doc_title_match.group(1).strip()
                continue

            # Check for Section header: "## Section ANC-01: Minimum Antenatal Visits Schedule"
            sec_match = re.match(r"^##\s+Section\s+([A-Za-z0-9\-]+):\s*(.+)$", line.strip())
            if sec_match:
                # Flush existing section if it has content
                if section_lines:
                    text_content = "".join(section_lines).strip()
                    if text_content:
                        tokens = tokenize(text_content)
                        # Top unique informative tokens for keyword indexing
                        informative_tokens = [t for t in tokens if len(t) > 3][:20]
                        chunks.append(
                            ProtocolChunk(
                                chunk_id=f"{doc_id}#{current_section_id}-c1",
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
                # Start new section
                current_section_id = sec_match.group(1).strip()
                current_section_title = sec_match.group(2).strip()
                section_lines = []
                section_start_line = idx
            else:
                section_lines.append(line)

        # Flush final section
        if section_lines:
            text_content = "".join(section_lines).strip()
            if text_content:
                tokens = tokenize(text_content)
                informative_tokens = [t for t in tokens if len(t) > 3][:20]
                chunks.append(
                    ProtocolChunk(
                        chunk_id=f"{doc_id}#{current_section_id}-c1",
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
    chunks = ingest_corpus()
    print(f"Successfully ingested {len(chunks)} chunks from corpus:")
    for c in chunks:
        print(f" - [{c.doc_id}] {c.section_id}: {c.section_title} ({c.token_count} tokens, lines {c.line_start}-{c.line_end})")
