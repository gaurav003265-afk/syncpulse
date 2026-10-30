/**
 * Speech Processing & Transcript Validation Module for SyncPulse TypeScript Engine.
 *
 * Implements Voice Input Pipeline Step 3:
 * - Identifies whether a voice transcript is clinically understandable.
 * - Distinguishes silence, conversational filler / background noise, and valid queries.
 * - Prevents spurious retrieval matches on stray acoustic filler words ('well', 'um', 'uh').
 * - Directs unclear voice recordings to honest safety text fallbacks.
 */

import { normalizeText, tokenize } from "./normalize.ts";

export const FILLER_TOKENS = new Set([
  "uh", "um", "er", "ah", "hmm", "well", "like", "okay", "ok",
  "yeah", "yep", "yes", "so", "just", "thing", "things", "stuff",
  "yesterday", "today", "tomorrow", "some", "actually", "basically",
  "you", "know", "mean", "right"
]);

export const PRONOUNS_AND_FUNCTION_WORDS = new Set([
  "i", "you", "we", "they", "he", "she", "it", "my", "your", "their", "our",
  "his", "her", "this", "that", "these", "those", "there", "here", "them",
  "me", "us", "him", "myself", "yourself", "the", "a", "an", "and", "or",
  "but", "with", "from", "at", "by", "for", "in", "on", "to", "of", "about",
  "what", "is", "please", "can", "should", "how", "when", "where", "why", "do"
]);

export interface TranscriptValidationTS {
  is_understandable: boolean;
  status: "valid" | "silence" | "noisy_unclear" | "too_short";
  cleaned_text: string;
  message: string;
}

export function validateTranscriptTS(rawTranscript: string): TranscriptValidationTS {
  if (!rawTranscript || !rawTranscript.trim()) {
    return {
      is_understandable: false,
      status: "silence",
      cleaned_text: "",
      message: "No speech detected (silence). Please speak into the microphone or use text entry.",
    };
  }

  const norm = normalizeText(rawTranscript);
  const tokens = tokenize(norm);

  if (!tokens || tokens.length === 0) {
    return {
      is_understandable: false,
      status: "silence",
      cleaned_text: "",
      message: "No recognizable words detected. Please try again.",
    };
  }

  // Filter out stopwords, pronouns, and acoustic fillers
  const contentTokens = tokens.filter(
    (t) => !FILLER_TOKENS.has(t) && !PRONOUNS_AND_FUNCTION_WORDS.has(t) && t.length > 1
  );

  if (contentTokens.length === 0) {
    return {
      is_understandable: false,
      status: "noisy_unclear",
      cleaned_text: norm,
      message: "Speech was unclear or contained only acoustic filler sounds. Please re-speak or type your question.",
    };
  }

  return {
    is_understandable: true,
    status: "valid",
    cleaned_text: norm,
    message: "Transcript is clear and ready for clinical triage.",
  };
}
