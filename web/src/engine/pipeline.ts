/**
 * Client-side pipeline orchestrator in TypeScript.
 * Provides instant on-device execution with identical logic and citations
 * to the Python core/pipeline.py.
 */

import { EscalationEngineTS } from "./escalation.ts";
import type { EscalationResult, MatchedRule } from "./escalation.ts";
import { normalizeText, tokenize } from "./normalize.ts";
import { BM25RetrieverTS } from "./retrieve.ts";
import type { RetrievedChunkTS } from "./retrieve.ts";
import { ScopeClassifierTS } from "./scope.ts";
import type { ScopeResult } from "./scope.ts";
import { validateTranscriptTS } from "./speech.ts";

export interface PipelineResponseTS {
  type: "escalate" | "refuse" | "answer" | "abstain";
  text: string;
  primary_citation: string | null;
  citations: string[];
  matched_rules: MatchedRule[];
  confidence: number;
  latency_ms: number;
  scope_category: string | null;
  negation_detected: boolean;
}

export class PipelineTS {
  private escalationEngine: EscalationEngineTS;
  private scopeClassifier: ScopeClassifierTS;
  private retriever: BM25RetrieverTS;

  constructor(abstainThreshold = 1.8) {
    this.escalationEngine = new EscalationEngineTS();
    this.scopeClassifier = new ScopeClassifierTS();
    this.retriever = new BM25RetrieverTS(abstainThreshold);
  }

  public checkEscalation(query: string): EscalationResult {
    return this.escalationEngine.check(query);
  }

  public processQuery(query: string): PipelineResponseTS {
    const t0 = performance.now();

    // Step 0: Input normalisation
    const norm = normalizeText(query);

    // -------------------------------------------------------------
    // STAGE 1: Deterministic Danger-Sign Escalation Check
    // Hard gate: fires BEFORE any retrieval or model reasoning!
    // -------------------------------------------------------------
    const escRes: EscalationResult = this.escalationEngine.check(query);
    if (escRes.escalate) {
      const elapsed = performance.now() - t0;
      const primary = escRes.matched_rules.length > 0 ? escRes.matched_rules[0] : null;
      const primaryCitation = primary ? primary.corpus_citation : null;

      let escalationText =
        `🚨 **REFER IMMEDIATELY: Obstetric / Neonatal / Medical Emergency Detected**\n\n` +
        `**Clinical Danger Sign:** ${primary ? primary.title : "Severe Emergency"}\n` +
        `**Action Protocol:** ${escRes.action_text}\n\n` +
        `**Protocol Citation:** ${primaryCitation}`;

      if (escRes.negation_detected) {
        escalationText +=
          `\n\n*(Note: Negation word detected in clinical text; ` +
          `safety rule escalated fail-safe per emergency protocol)*`;
      }

      return {
        type: "escalate",
        text: escalationText,
        primary_citation: primaryCitation,
        citations: primaryCitation ? [primaryCitation] : [],
        matched_rules: escRes.matched_rules,
        confidence: 1.0,
        latency_ms: Math.round(elapsed * 100) / 100,
        scope_category: "EMERGENCY_ESCALATION",
        negation_detected: escRes.negation_detected,
      };
    }

    // -------------------------------------------------------------
    // STAGE 1.5: Voice Transcript Understandability & Acoustic Noise Filter
    // -------------------------------------------------------------
    const valRes = validateTranscriptTS(query);
    if (!valRes.is_understandable) {
      const elapsed = performance.now() - t0;
      return {
        type: "abstain",
        text: valRes.message,
        primary_citation: null,
        citations: [],
        matched_rules: [],
        confidence: 0.0,
        latency_ms: Math.round(elapsed * 100) / 100,
        scope_category: `VOICE_${valRes.status.toUpperCase()}`,
        negation_detected: escRes.negation_detected,
      };
    }

    // -------------------------------------------------------------
    // STAGE 2: Scope and Refusal Classification
    // -------------------------------------------------------------
    const scopeRes: ScopeResult = this.scopeClassifier.classify(query);
    if (!scopeRes.is_in_scope) {
      const elapsed = performance.now() - t0;
      return {
        type: "refuse",
        text:
          scopeRes.redirect_message ||
          "Request is outside protocol scope. Please consult a Medical Officer.",
        primary_citation: null,
        citations: [],
        matched_rules: [],
        confidence: 0.98,
        latency_ms: Math.round(elapsed * 100) / 100,
        scope_category: scopeRes.scope_category,
        negation_detected: escRes.negation_detected,
      };
    }

    // -------------------------------------------------------------
    // STAGE 3: BM25 Protocol Chunk Retrieval
    // -------------------------------------------------------------
    const retrievedChunks: RetrievedChunkTS[] = this.retriever.search(query, 3);
    const shouldAbstain = this.retriever.shouldAbstain(retrievedChunks);

    // -------------------------------------------------------------
    // STAGE 4: Extractive Grounded Answer Composition
    // -------------------------------------------------------------
    if (shouldAbstain || retrievedChunks.length === 0) {
      const elapsed = performance.now() - t0;
      return {
        type: "abstain",
        text:
          "The requested information was not found in the official frontline protocol documents. " +
          "Frontline workers must not guess clinical steps. " +
          "Please consult the Medical Officer at the Primary Health Centre (PHC) for clinical guidance.",
        primary_citation: null,
        citations: [],
        matched_rules: [],
        confidence: 0.0,
        latency_ms: Math.round(elapsed * 100) / 100,
        scope_category: "OUT_OF_INDEX_ABSTAIN",
        negation_detected: escRes.negation_detected,
      };
    }

    const topChunk = retrievedChunks[0];
    const qTokens = new Set(tokenize(norm));
    const lines = topChunk.text
      .split("\n")
      .map((l) => l.trim())
      .filter((l) => l.length > 0);

    const scoredLines: { line: string; overlap: number }[] = [];
    for (const line of lines) {
      const lineNorm = normalizeText(line);
      const lineTokens = new Set(tokenize(lineNorm));
      let overlap = 0;
      for (const tok of qTokens) {
        if (lineTokens.has(tok)) overlap++;
      }
      if (/^(?:\d+[\.\)]|[\-\*])\s+/.test(line)) {
        overlap += 1;
      }
      scoredLines.push({ line, overlap });
    }

    let selectedBody = "";
    if (lines.length <= 8) {
      selectedBody = lines
        .map((l) => `• ${l.replace(/^[-*•0-9.\s]+/, "")}`)
        .join("\n");
    } else {
      const indexed = scoredLines.map((item, idx) => ({ idx, overlap: item.overlap }));
      indexed.sort((a, b) => b.overlap - a.overlap);
      const bestIndices = indexed.slice(0, 5).map((x) => x.idx).sort((a, b) => a - b);
      selectedBody = bestIndices
        .map((i) => `• ${lines[i].replace(/^[-*•0-9.\s]+/, "")}`)
        .join("\n");
    }

    const primaryCitation = topChunk.citation;
    const citations = retrievedChunks.map((c) => c.citation);
    const confidence = Math.min(
      0.99,
      Math.max(0.5, topChunk.score / (topChunk.score + 5.0))
    );

    const formattedAnswer =
      `**Protocol Guidance:** ${topChunk.section_title}\n\n` +
      `${selectedBody}\n\n` +
      `**Official Protocol Source:** ${primaryCitation}`;

    const elapsed = performance.now() - t0;
    return {
      type: "answer",
      text: formattedAnswer,
      primary_citation: primaryCitation,
      citations,
      matched_rules: [],
      confidence: Math.round(confidence * 100) / 100,
      latency_ms: Math.round(elapsed * 100) / 100,
      scope_category: "IN_SCOPE_PROTOCOL",
      negation_detected: escRes.negation_detected,
    };
  }
}
