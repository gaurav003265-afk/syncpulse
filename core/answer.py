"""
Extractive answer composition engine.

Extracts factual sentences directly from retrieved protocol chunks.
Guarantees:
- Zero hallucination (every claim grounded in protocol text).
- Every answer includes exact document and section citations.
- Clean abstention when query is unsupported by the corpus.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional

from core.normalize import normalize_text, tokenize
from core.retrieve import RetrievedChunk


@dataclass
class AnswerResult:
    answer_type: str  # "answer", "abstain", "refusal", "escalate"
    answer_text: str
    primary_citation: Optional[str]
    citations: List[str]
    confidence_score: float
    retrieved_chunks: List[Dict[str, Any]]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "answer_type": self.answer_type,
            "answer_text": self.answer_text,
            "primary_citation": self.primary_citation,
            "citations": self.citations,
            "confidence_score": self.confidence_score,
            "retrieved_chunks": self.retrieved_chunks,
        }


class AnswerComposer:
    def __init__(self, abstention_message: Optional[str] = None):
        self.abstention_message = abstention_message or (
            "The requested information was not found in the official frontline protocol documents. "
            "Frontline workers must not guess clinical steps. "
            "Please consult the Medical Officer at the Primary Health Centre (PHC) for clinical guidance."
        )

    def compose(
        self,
        query: str,
        retrieved_chunks: List[RetrievedChunk],
        abstain: bool = False,
    ) -> AnswerResult:
        """
        Composes an extractive answer strictly grounded in retrieved chunks.
        """
        if abstain or not retrieved_chunks:
            return AnswerResult(
                answer_type="abstain",
                answer_text=self.abstention_message,
                primary_citation=None,
                citations=[],
                confidence_score=0.0,
                retrieved_chunks=[c.to_dict() for c in retrieved_chunks],
            )

        top_chunk = retrieved_chunks[0]
        q_norm = normalize_text(query)
        q_tokens = set(tokenize(q_norm))

        # Split text into lines / sentences to identify most relevant guidance
        lines = [line.strip() for line in top_chunk.text.split("\n") if line.strip()]

        # Score lines based on overlap with query tokens
        scored_lines = []
        for line in lines:
            line_norm = normalize_text(line)
            line_tokens = set(tokenize(line_norm))
            overlap = len(q_tokens.intersection(line_tokens))
            # Boost numbered steps or bullet points
            if re.match(r"^(?:\d+[\.\)]|[\-\*])\s+", line):
                overlap += 1
            scored_lines.append((line, overlap))

        # If lines are short structured bullets (e.g. protocol steps), select top relevant or preserve whole section
        if len(lines) <= 8:
            selected_body = "\n".join(f"• {l.lstrip('-*•0123456789. ')}" for l in lines)
        else:
            # Sort top 4-5 relevant lines while maintaining original protocol document order
            best_line_indices = sorted(
                sorted(range(len(scored_lines)), key=lambda i: scored_lines[i][1], reverse=True)[:5]
            )
            selected_body = "\n".join(f"• {lines[i].lstrip('-*•0123456789. ')}" for i in best_line_indices)

        # Build citation list
        citations = [c.citation for c in retrieved_chunks]
        primary_citation = retrieved_chunks[0].citation

        # Compute confidence: normalized by top BM25 score
        confidence = min(0.99, max(0.50, top_chunk.score / (top_chunk.score + 5.0)))

        formatted_answer = (
            f"**Protocol Guidance:** {top_chunk.section_title}\n\n"
            f"{selected_body}\n\n"
            f"**Official Protocol Source:** {primary_citation}"
        )

        return AnswerResult(
            answer_type="answer",
            answer_text=formatted_answer,
            primary_citation=primary_citation,
            citations=citations,
            confidence_score=round(confidence, 2),
            retrieved_chunks=[c.to_dict() for c in retrieved_chunks],
        )
