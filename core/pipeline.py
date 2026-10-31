"""
End-to-end processing pipeline for the Frontline Health-Worker Companion.

Executes the strict 4-stage pipeline for every question:
  raw input
  -> normalise
  -> [1] ESCALATION LAYER (deterministic rules; if triggered, returns REFER IMMEDIATELY at once)
  -> [2] SCOPE / REFUSAL CHECK (dosing, prescribing, drug choices, diagnosis beyond protocol, non-health)
  -> [3] RETRIEVAL (BM25 baseline over section-tagged chunks)
  -> [4] ANSWER COMPOSITION (extractive grounded sentences with exact protocol citations or clean abstention)
"""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional

from core.answer import AnswerComposer, AnswerResult
from core.escalation import EscalationEngine, EscalationResult
from core.interfaces import IAnswerComposer, IEscalationEngine, IProtocolRetriever, IScopeClassifier
from core.model_adapter import (
    BaseOfflineModelAdapter,
    CitationValidator,
    GenerationOutput,
    LocalQuantizedModelAdapter,
)
from core.normalize import normalize_text
from core.retrieve import BM25Retriever, RetrievedChunk
from core.scope import ScopeClassifier, ScopeResult
from core.speech import validate_transcript


@dataclass
class PipelineResponse:
    type: str  # "escalate", "refuse", "answer", "abstain"
    text: str
    primary_citation: Optional[str]
    citations: List[str]
    matched_rules: List[Dict[str, Any]]
    confidence: float
    latency_ms: float
    scope_category: Optional[str]
    negation_detected: bool

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class FrontlineCompanionPipeline:
    def __init__(
        self,
        rules_path: Optional[str] = None,
        knowledge_pack_dir: Optional[str] = None,
        abstain_threshold: float = 1.8,
        adapter: Optional[BaseOfflineModelAdapter] = None,
        escalation_engine=None,
        scope_classifier=None,
        retriever=None,
        composer=None,
    ):
        self.escalation_engine = escalation_engine or EscalationEngine(rules_path)
        self.scope_classifier = scope_classifier or ScopeClassifier()
        self.retriever = retriever or BM25Retriever(knowledge_pack_dir, abstain_threshold=abstain_threshold)
        self.composer = composer or AnswerComposer()
        self.adapter = adapter or LocalQuantizedModelAdapter()
        self.citation_validator = CitationValidator()
        self.citation_validator.load_from_chunks(self.retriever.chunks_data)

    def process_query(self, query: str) -> PipelineResponse:
        """
        Processes a health-worker question through the complete 4-stage offline pipeline.
        """
        t0 = time.perf_counter()

        # Step 0: Input normalisation
        norm_query = normalize_text(query)

        # -------------------------------------------------------------
        # STAGE 1: Deterministic Danger-Sign Escalation Check
        # Hard gate: fires BEFORE any retrieval or model reasoning!
        # -------------------------------------------------------------
        esc_res: EscalationResult = self.escalation_engine.check(query)
        if esc_res.escalate:
            elapsed = (time.perf_counter() - t0) * 1000.0
            primary = esc_res.matched_rules[0] if esc_res.matched_rules else None
            primary_citation = primary.corpus_citation if primary else None
            matched_dicts = [asdict(r) for r in esc_res.matched_rules]

            action = esc_res.action_text or "REFER IMMEDIATELY to FRU/Hospital. Call 108."
            title = primary.title if primary else "Emergency"
            escalation_text = f"{title}: {action} ({primary_citation}). Refer immediately."
            if esc_res.negation_detected:
                escalation_text += " (Note: Negation word detected in clinical text; escalating fail-safe per emergency protocol)."

            return PipelineResponse(
                type="escalate",
                text=escalation_text,
                primary_citation=primary_citation,
                citations=[primary_citation] if primary_citation else [],
                matched_rules=matched_dicts,
                confidence=1.0,
                latency_ms=round(elapsed, 2),
                scope_category="EMERGENCY_ESCALATION",
                negation_detected=esc_res.negation_detected,
            )

        # -------------------------------------------------------------
        # STAGE 1.5: Voice Transcript Understandability & Acoustic Noise Filter
        # Rejects silence, pure conversational fillers, and unintelligible recordings
        # -------------------------------------------------------------
        val_res = validate_transcript(query)
        if not val_res.is_understandable:
            elapsed = (time.perf_counter() - t0) * 1000.0
            return PipelineResponse(
                type="abstain",
                text=val_res.message,
                primary_citation=None,
                citations=[],
                matched_rules=[],
                confidence=0.0,
                latency_ms=round(elapsed, 2),
                scope_category=f"VOICE_{val_res.status.upper()}",
                negation_detected=esc_res.negation_detected,
            )

        # -------------------------------------------------------------
        # STAGE 2: Scope and Refusal Classification
        # Protects paramedical boundary (no unapproved antibiotic dosing / surgery / non-health)
        # -------------------------------------------------------------
        scope_res: ScopeResult = self.scope_classifier.classify(query)
        if not scope_res.is_in_scope:
            elapsed = (time.perf_counter() - t0) * 1000.0
            return PipelineResponse(
                type="refuse",
                text=scope_res.redirect_message or "Request is outside protocol scope. Please consult a Medical Officer (SCP-1.2).",
                primary_citation="SCP-1.2",
                citations=["SCP-1.2"],
                matched_rules=[],
                confidence=0.98,
                latency_ms=round(elapsed, 2),
                scope_category=scope_res.scope_category,
                negation_detected=esc_res.negation_detected,
            )

        # -------------------------------------------------------------
        # STAGE 3: BM25 Protocol Chunk Retrieval
        # -------------------------------------------------------------
        retrieved_chunks: List[RetrievedChunk] = self.retriever.search(query, top_k=3)
        should_abstain = self.retriever.should_abstain(retrieved_chunks)

        # -------------------------------------------------------------
        # STAGE 4: Extractive Grounded Answer Composition & Citation Gate
        # -------------------------------------------------------------
        ans_res: AnswerResult = self.composer.compose(
            query=query,
            retrieved_chunks=retrieved_chunks,
            abstain=should_abstain,
        )

        # Strict Citation Validation Gate: verify citations point strictly to ingested chunks
        validated_citations = [
            c for c in ans_res.citations if self.citation_validator.is_valid(c)
        ]
        primary_citation = ans_res.primary_citation
        if primary_citation and not self.citation_validator.is_valid(primary_citation):
            # Unvalidated citation detected: reject to prevent hallucination
            primary_citation = None
            validated_citations = []
            ans_res.answer_type = "abstain"
            ans_res.answer_text = (
                "Official protocol citation could not be verified against the local knowledge pack. "
                "Consult the Medical Officer at the Primary Health Centre."
            )

        elapsed = (time.perf_counter() - t0) * 1000.0
        return PipelineResponse(
            type=ans_res.answer_type,
            text=ans_res.answer_text,
            primary_citation=primary_citation,
            citations=validated_citations,
            matched_rules=[],
            confidence=ans_res.confidence_score,
            latency_ms=round(elapsed, 2),
            scope_category="IN_SCOPE_PROTOCOL",
            negation_detected=esc_res.negation_detected,
        )


if __name__ == "__main__":
    import sys
    if sys.stdout.encoding != "utf-8":
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    pipeline = FrontlineCompanionPipeline()
    test_queries = [
        "Woman 7 months pregnant has heavy vaginal bleeding",
        "What is the schedule for routine ANC visits?",
        "What dose of ciprofloxacin should I prescribe?",
        "How to prepare 1 liter of ORS solution?",
        "Who won the cricket world cup?",
    ]
    for q in test_queries:
        res = pipeline.process_query(q)
        print(f"\nQ: {q}")
        print(f"Type: {res.type} ({res.latency_ms} ms)")
        print(f"Citation: {res.primary_citation}")
        print(f"Text: {res.text[:120]}...")
