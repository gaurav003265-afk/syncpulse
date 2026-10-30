"""
Deterministic BM25 retrieval engine over protocol chunks.

Offline-first, zero-model footprint, pure Python BM25Okapi scoring.
Provides section-level precision and exact citations for frontline health workers.
"""

from __future__ import annotations

import json
import math
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from core.ingest import ProtocolChunk, ingest_corpus
from core.normalize import normalize_text, tokenize


@dataclass
class RetrievedChunk:
    chunk_id: str
    doc_id: str
    doc_title: str
    section_id: str
    section_title: str
    line_start: int
    line_end: int
    text: str
    score: float
    citation: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


STOPWORDS = {
    "what", "is", "the", "for", "of", "and", "in", "to", "a", "an",
    "protocol", "guidelines", "please", "can", "should", "i", "we", "be", "do",
    "how", "when", "where", "why", "at", "by", "on", "with", "from"
}
CODE_MIX_SYNONYMS: Dict[str, List[str]] = {
    "tika": ["vaccine", "immunisation", "injection"],
    "soojan": ["swelling", "edema"],
    "vaapu": ["swelling", "edema"],
    "dard": ["pain", "soreness", "ache"],
    "noppi": ["pain", "ache"],
    "jwaram": ["fever", "temperature"],
    "bukhar": ["fever", "temperature"],
    "virechanalu": ["diarrhea", "stool", "hydration"],
    "dast": ["diarrhea", "stool", "hydration"],
    "prasav": ["delivery", "labor", "childbirth"],
    "prasavam": ["delivery", "labor", "childbirth"],
    "garbham": ["pregnancy", "antenatal", "maternal"],
    "garbhavathi": ["pregnancy", "pregnant", "maternal"],
    "palu": ["breastmilk", "feeding", "breastfeed"],
    "doodh": ["milk", "feeding", "breastfeed"],
    "bacha": ["child", "baby", "infant"],
    "shishu": ["newborn", "infant", "baby"],
    "pilla": ["child", "baby"],
    "pilladi": ["child", "baby"],
    "pillaki": ["child", "baby"],
    "neellu": ["water", "hydration"],
    "pani": ["water"],
    "kalapali": ["mix", "prepare", "liter"],
    "ghol": ["solution", "mix", "ors"],
    "aakali": ["appetite", "feeding"],
    "bhookh": ["appetite", "feeding"],
}


class BM25Retriever:
    def __init__(
        self,
        knowledge_pack_dir: Optional[str] = None,
        k1: float = 1.5,
        b: float = 0.75,
        abstain_threshold: float = 1.8,
    ):
        self.k1 = k1
        self.b = b
        self.abstain_threshold = abstain_threshold

        root_dir = Path(__file__).resolve().parent.parent
        if knowledge_pack_dir is None:
            self.pack_dir = root_dir / "data" / "knowledge_pack"
        else:
            self.pack_dir = Path(knowledge_pack_dir)

        chunks_file = self.pack_dir / "chunks.json"
        bm25_file = self.pack_dir / "bm25_index.json"

        if chunks_file.exists() and bm25_file.exists():
            with open(chunks_file, "r", encoding="utf-8") as f:
                self.chunks_data = json.load(f)
            with open(bm25_file, "r", encoding="utf-8") as f:
                self.bm25_data = json.load(f)
            self.doc_lens = self.bm25_data.get("doc_lens", [])
            self.avg_dl = self.bm25_data.get("avg_dl", 100.0)
            self.inverted_index = self.bm25_data.get("inverted_index", {})
            self.doc_count = self.bm25_data.get("doc_count", len(self.chunks_data))
        else:
            # Fallback to dynamic ingest if knowledge pack not pre-built
            chunks = ingest_corpus()
            self.chunks_data = [c.to_dict() for c in chunks]
            self.doc_lens = []
            self.inverted_index = {}
            for idx, c in enumerate(chunks):
                toks = tokenize(f"{c.doc_title} {c.section_title} {' '.join(c.keywords)} {c.text}")
                self.doc_lens.append(len(toks))
                for t in toks:
                    if t not in self.inverted_index:
                        self.inverted_index[t] = []
                    # Find if already exists
                    found = False
                    for pair in self.inverted_index[t]:
                        if pair[0] == idx:
                            pair[1] += 1
                            found = True
                            break
                    if not found:
                        self.inverted_index[t].append([idx, 1])
            self.doc_count = len(self.chunks_data)
            self.avg_dl = sum(self.doc_lens) / max(1, self.doc_count)

        # Precompute IDF values for every token in vocabulary
        self.idf: Dict[str, float] = {}
        for tok, postings in self.inverted_index.items():
            n = len(postings)  # number of documents containing token
            # Standard Lucene/BM25Okapi IDF formula
            self.idf[tok] = math.log(1.0 + (self.doc_count - n + 0.5) / (n + 0.5))

    def search(self, query: str, top_k: int = 3) -> List[RetrievedChunk]:
        """
        Retrieves top_k citable chunks for the query using BM25Okapi.
        """
        norm_query = normalize_text(query)
        q_tokens = tokenize(norm_query)

        if not q_tokens:
            return []

        # Filter stopwords if informative tokens exist
        informative_q = [t for t in q_tokens if t not in STOPWORDS]
        active_tokens = informative_q if informative_q else q_tokens

        # Expand tokens with code-mix vernacular equivalents
        search_tokens = list(active_tokens)
        for tok in active_tokens:
            if tok in CODE_MIX_SYNONYMS:
                search_tokens.extend(CODE_MIX_SYNONYMS[tok])

        doc_scores: Dict[int, float] = {i: 0.0 for i in range(self.doc_count)}

        for tok in search_tokens:
            # Check exact token or prefix in vocabulary
            matching_vocab_keys = []
            if tok in self.inverted_index:
                matching_vocab_keys.append(tok)
            else:
                # Strip common English inflectional suffixes (-ing, -ed, -es, -s, -tion)
                stem = re.sub(r"(?:ing|tion|ed|es|s)$", "", tok)
                if len(stem) >= 4:
                    for v_tok in self.inverted_index:
                        v_stem = re.sub(r"(?:ing|tion|ed|es|s)$", "", v_tok)
                        if v_stem == stem or (v_tok.startswith(stem) and len(v_tok) <= len(stem) + 4):
                            matching_vocab_keys.append(v_tok)
                            if len(matching_vocab_keys) >= 3:
                                break

            for v_tok in matching_vocab_keys:
                idf_val = self.idf.get(v_tok, 0.0)
                postings = self.inverted_index.get(v_tok, [])
                for doc_idx, tf in postings:
                    dl = self.doc_lens[doc_idx]
                    denom = tf + self.k1 * (1.0 - self.b + self.b * (dl / self.avg_dl))
                    term_score = idf_val * (tf * (self.k1 + 1.0)) / max(0.001, denom)

                    # Boost section title matches
                    c_data = self.chunks_data[doc_idx]
                    sec_title_lower = c_data["section_title"].lower()
                    if v_tok in sec_title_lower:
                        term_score *= 1.8

                    doc_scores[doc_idx] += term_score

        # Sort documents by score descending
        ranked = sorted(doc_scores.items(), key=lambda x: x[1], reverse=True)

        results: List[RetrievedChunk] = []
        for doc_idx, score in ranked[:top_k]:
            if score <= 0.0:
                continue
            c = self.chunks_data[doc_idx]
            citation_str = f"[{c['doc_id']}] Section {c['section_id']}: {c['section_title']} (Lines {c['line_start']}-{c['line_end']})"
            results.append(
                RetrievedChunk(
                    chunk_id=c["chunk_id"],
                    doc_id=c["doc_id"],
                    doc_title=c["doc_title"],
                    section_id=c["section_id"],
                    section_title=c["section_title"],
                    line_start=c["line_start"],
                    line_end=c["line_end"],
                    text=c["text"],
                    score=round(score, 3),
                    citation=citation_str,
                )
            )

        return results

    def should_abstain(self, retrieved: List[RetrievedChunk]) -> bool:
        """
        Determines whether to abstain based on retrieval confidence score.
        If no chunks found or top score below calibrated threshold -> abstain.
        """
        if not retrieved:
            return True
        top_score = retrieved[0].score
        return top_score < self.abstain_threshold
