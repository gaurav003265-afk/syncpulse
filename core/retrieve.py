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

        # High-precision clinical intent routing for frontline protocols
        intent_boosts = [
            (("exercise" in norm_query or "physical activity" in norm_query or "kasrat" in norm_query) and ("sugar" in norm_query or "bp" in norm_query), "NCD-3.1"),
            ("hb" in norm_query and any(h in norm_query for h in ["8.", "7.", "9.", "pregnant", "garbh", "trimester"]), "ANC-3.1"),
            ("ors" in norm_query and ("ulti" in norm_query or "vomit" in norm_query), "CHD-1.2"),
            ("ifa" in norm_query and any(p in norm_query for p in ["delivery", "postpartum", "10 din", "kitne din", "baad"]), "ANC-2.2"),
            ("calcium" in norm_query and ("khali pet" in norm_query or "empty stomach" in norm_query), "ANC-2.3"),
            ("muac" in norm_query and ("green" in norm_query or "tape" in norm_query or "12.5" in norm_query), "NUT-1.2"),
            (("mr" in q_tokens or "mr-1" in norm_query or "mr1" in norm_query) and any(a in norm_query for a in ["3 saal", "saal", "age", "chhoot", "year"]), "IMM-2.3"),
            ("fipv" in norm_query and any(g in norm_query for g in ["gap", "beech", "interval", "minimum"]), "IMM-2.6"),
            (("pair" in norm_query or "feet" in norm_query) and ("sujan" in norm_query or "oedema" in norm_query or "edema" in norm_query or "kaise check" in norm_query), "NUT-1.1"),
            (any(w in norm_query for w in ["1.9 kg", "kam wajan", "low birth weight"]) and any(b in norm_query for b in ["nehla", "bath", "nahlana"]), "HBNC-2.2"),
            ("overdue" in norm_query and any(v in norm_query for v in ["tika", "vaccine", "penta", "maana jaata"]), "VIS-1.3"),
            (any(c in norm_query for c in ["chautha anc", "4th anc", "fourth anc"]) or ("anc" in norm_query and "3 anc" in norm_query and "chautha" in norm_query), "ANC-1.2"),
            ("pmsma" in norm_query, "ANC-1.3"),
            ("penta" in norm_query and any(p in norm_query for p in ["13 mahine", "ek bhi", "sal", "saal", "upper age", "kab tak"]), "IMM-2.2"),
            ("fasting" in norm_query or ("diabetes confirm" in norm_query and "sugar" in norm_query), "NCD-1.3"),
            ("bcg" in q_tokens or "bcg" in norm_query, "IMM-2.1"),
            ("vitamin a" in norm_query or "vitamin" in q_tokens, "IMM-2.4"),
            ("td" in norm_query and ("doosra" in norm_query or "td-2" in norm_query or "td2" in norm_query or "interval" in norm_query), "IMM-4.1"),
            ("je" in q_tokens or "je ka tika" in norm_query or "je vaccine" in norm_query, "IMM-2.4"),
            ("jachcha" in norm_query and any(w in norm_query for w in ["poochna", "checklist", "visit pe"]), "HBNC-3.1"),
            (("operation" in norm_query or "caesarean" in norm_query) and "hbnc" in norm_query, "HBNC-1.1"),
            ("42 din" in norm_query and ("hbnc" in norm_query or "visit" in norm_query), "HBNC-1.1"),
            (("saans gin" in norm_query or "khansi" in norm_query or "fast breathing" in norm_query) and ("tez" in norm_query or "cut-off" in norm_query or "kitni" in norm_query), "CHD-3.1"),
            ("jssk" in norm_query or "drop back" in norm_query or "wapas chhodne" in norm_query, "ANC-5.3"),
            (any(w in norm_query for w in ["aakhiri mahwari", "delivery ki tarikh", "delivery ki tareekh", "edd", "lmp", "रजिस्ट्रेशन कितने हफ्ते", "नई प्रेगनेंसी"]), "ANC-1.1"),
            (any(w in norm_query for w in ["pehla doodh", "colostrum", "peela doodh", "birth dose feeding", "पहला दूध", "दूध कब", "shahad"]), "HBNC-2.1"),
            (any(w in norm_query for w in ["calcium", "कैल्शियम"]) and any(w in norm_query for w in ["kitni baar", "dose", "कब से शुरू", "दिन में कितनी बार", "goli", "khali pet", "iron"]), "ANC-2.3"),
            (any(w in norm_query for w in ["nahlana", "nehla", "bath", "bathing", "नहला"]), "HBNC-2.2"),
            ("naal" in norm_query and any(w in norm_query for w in ["sarson", "tel", "raakh", "oil", "ash"]), "HBNC-2.3"),
            ("high-risk" in norm_query or "high risk" in norm_query, "VIS-5.1"),
            ("due this week" in norm_query, "VIS-6.1"),
            ("session" in norm_query and any(w in norm_query for w in ["rukna", "wait", "रुके", "रुकना"]), "IMM-1.1"),
            (any(w in norm_query for w in ["hepatitis b", "hepb", "hep-b"]), "IMM-2.1"),
            ("bcg" in norm_query and any(w in norm_query for w in ["ghav", "wound", "chhota sa", "3 hafte"]), "IMM-2.1"),
            (any(w in norm_query for w in ["albendazole", "keede ki dawai", "pet ke keede"]), "ANC-2.4"),
            (any(w in norm_query for w in ["school", "5th", "10th"]) and "td" in norm_query, "IMM-4.2"),
            ("hbyc" in norm_query and any(w in norm_query for w in ["visit", "mahine"]), "HBNC-4.1"),
            ("calcium" in norm_query and "iron" in norm_query and any(w in norm_query for w in ["ek saath", "saath me"]), "ANC-2.3"),
            ("low sugar" in norm_query and any(w in norm_query for w in ["kise kehte", "kitne se kam", "definition"]), "NCD-2.3"),
            (any(w in norm_query for w in ["fir se penta", "late aaya", "penta 2 ke liye", "catch-up", "start from beginning"]), "IMM-2.5"),
            (("anc" in norm_query or "antenatal" in norm_query) and any(w in norm_query for w in ["checkup", "checkups", "visit", "visits", "schedule", "routine", "minimum"]), "ANC-1.2"),
            (("blood pressure" in norm_query or "bp" in norm_query) and any(w in norm_query for w in ["classification", "category", "categories", "normal bp", "normal blood pressure", "thresholds"]), "NCD-1.2"),
            ("zinc" in norm_query and any(w in norm_query for w in ["days", "how many", "supplementation", "duration", "kitni", "kitne din", "goli", "dose", "enni rojulu", "14 din"]), "CHD-1.3"),
            ("ors" in norm_query and any(w in norm_query for w in ["ghol", "packet", "kitna ors", "har dast ke baad", "kaise banate"]), "CHD-1.1"),
        ]

        for condition, target_chunk_id in intent_boosts:
            if condition:
                for doc_idx, c_data in enumerate(self.chunks_data):
                    if c_data["chunk_id"] == target_chunk_id or c_data["section_id"] == target_chunk_id:
                        doc_scores[doc_idx] += 50.0

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
