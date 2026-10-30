"""
Speech Processing & Transcript Validation Module for SyncPulse.

Implements Voice Input Pipeline Step 3:
- Identifies whether a voice transcript is clinically understandable.
- Distinguishes silence, conversational filler / background noise, and valid queries.
- Prevents spurious retrieval matches on stray acoustic filler words ('well', 'um', 'uh').
- Directs unclear voice recordings to honest safety text fallbacks.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Dict, List, Optional, Set, Tuple

from core.normalize import normalize_text, tokenize
from core.retrieve import STOPWORDS

# Conversational hesitation fillers and low-information acoustic noise tokens
FILLER_TOKENS: Set[str] = {
    "uh", "um", "er", "ah", "hmm", "well", "like", "okay", "ok",
    "yeah", "yep", "yes", "so", "just", "thing", "things", "stuff",
    "yesterday", "today", "tomorrow", "some", "actually", "basically",
    "you", "know", "mean", "right"
}

PRONOUNS_AND_FUNCTION_WORDS: Set[str] = {
    "i", "you", "we", "they", "he", "she", "it", "my", "your", "their", "our",
    "his", "her", "this", "that", "these", "those", "there", "here", "them",
    "me", "us", "him", "myself", "yourself", "the", "a", "an", "and", "or",
    "but", "with", "from", "at", "by", "for", "in", "on", "to", "of", "about"
}

NON_CONTENT_TOKENS: Set[str] = STOPWORDS.union(FILLER_TOKENS).union(PRONOUNS_AND_FUNCTION_WORDS)


@dataclass
class TranscriptValidation:
    is_understandable: bool
    status: str  # "valid", "silence", "noisy_unclear", "too_short"
    cleaned_text: str
    message: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def validate_transcript(raw_transcript: str) -> TranscriptValidation:
    """
    Validates transcribed audio to verify it contains intelligible clinical intent
    before passing into retrieval or language generation.
    """
    if not raw_transcript or not raw_transcript.strip():
        return TranscriptValidation(
            is_understandable=False,
            status="silence",
            cleaned_text="",
            message="No speech detected (silence). Please speak into the microphone or use text entry.",
        )

    norm = normalize_text(raw_transcript)
    tokens = tokenize(norm)

    if not tokens:
        return TranscriptValidation(
            is_understandable=False,
            status="silence",
            cleaned_text="",
            message="No recognizable words detected. Please try again.",
        )

    # Filter out stopwords, pronouns, and acoustic fillers
    content_tokens = [t for t in tokens if t not in NON_CONTENT_TOKENS and len(t) > 1]

    if not content_tokens:
        return TranscriptValidation(
            is_understandable=False,
            status="noisy_unclear",
            cleaned_text=norm,
            message="Speech was unclear or contained only acoustic filler sounds. Please re-speak or type your question.",
        )

    return TranscriptValidation(
        is_understandable=True,
        status="valid",
        cleaned_text=norm,
        message="Transcript is clear and ready for clinical triage.",
    )
