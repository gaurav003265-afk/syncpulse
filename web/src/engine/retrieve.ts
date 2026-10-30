/**
 * BM25 retrieval engine in TypeScript for client-side offline execution.
 * Full parity with core/retrieve.py.
 */

import bm25Data from "../data/bm25_index.json" with { type: "json" };
import chunksData from "../data/chunks.json" with { type: "json" };
import { normalizeText, tokenize } from "./normalize.ts";

export interface RetrievedChunkTS {
  chunk_id: string;
  doc_id: string;
  doc_title: string;
  section_id: string;
  section_title: string;
  line_start: number;
  line_end: number;
  text: string;
  score: number;
  citation: string;
}

const STOPWORDS = new Set([
  "what", "is", "the", "for", "of", "and", "in", "to", "a", "an",
  "protocol", "guidelines", "please", "can", "should", "i", "we", "be", "do",
  "how", "when", "where", "why", "at", "by", "on", "with", "from"
]);

const CODE_MIX_SYNONYMS: Record<string, string[]> = {
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
};

export class BM25RetrieverTS {
  private k1: number;
  private b: number;
  private avgDl: number;
  private docLens: number[];
  private invertedIndex: Record<string, [number, number][]>;
  private chunks: any[];
  private idf: Map<string, number>;
  private abstainThreshold: number;

  constructor(abstainThreshold = 1.8) {
    this.k1 = (bm25Data as any).k1 || 1.5;
    this.b = (bm25Data as any).b || 0.75;
    this.avgDl = (bm25Data as any).avg_dl || 100.0;
    this.docLens = (bm25Data as any).doc_lens || [];
    this.invertedIndex = (bm25Data as any).inverted_index || {};
    this.chunks = (chunksData as any[]) || [];
    this.abstainThreshold = abstainThreshold;

    this.idf = new Map();
    const docCount = this.chunks.length;
    for (const [tok, postings] of Object.entries(this.invertedIndex)) {
      const n = postings.length;
      const idfVal = Math.log(1.0 + (docCount - n + 0.5) / (n + 0.5));
      this.idf.set(tok, idfVal);
    }
  }

  public search(query: string, topK = 3): RetrievedChunkTS[] {
    const norm = normalizeText(query);
    const qTokens = tokenize(norm);
    if (qTokens.length === 0) return [];

    const informative = qTokens.filter(t => !STOPWORDS.has(t));
    const activeTokens = informative.length > 0 ? informative : qTokens;

    const searchTokens = [...activeTokens];
    for (const tok of activeTokens) {
      if (CODE_MIX_SYNONYMS[tok]) {
        searchTokens.push(...CODE_MIX_SYNONYMS[tok]);
      }
    }

    const docScores = new Float32Array(this.chunks.length);

    for (const tok of searchTokens) {
      let matchingKeys: string[] = [];
      if (this.invertedIndex[tok]) {
        matchingKeys.push(tok);
      } else {
        const stem = tok.replace(/(?:ing|tion|ed|es|s)$/, "");
        if (stem.length >= 4) {
          for (const vTok of Object.keys(this.invertedIndex)) {
            const vStem = vTok.replace(/(?:ing|tion|ed|es|s)$/, "");
            if (vStem === stem || (vTok.startsWith(stem) && vTok.length <= stem.length + 4)) {
              matchingKeys.push(vTok);
              if (matchingKeys.length >= 3) break;
            }
          }
        }
      }

      for (const vTok of matchingKeys) {
        const idfVal = this.idf.get(vTok) || 0.0;
        const postings = this.invertedIndex[vTok] || [];
        for (const [docIdx, tf] of postings) {
          const dl = this.docLens[docIdx];
          const denom = tf + this.k1 * (1.0 - this.b + this.b * (dl / this.avgDl));
          let termScore = idfVal * (tf * (this.k1 + 1.0)) / Math.max(0.001, denom);

          const secTitle = (this.chunks[docIdx].section_title || "").toLowerCase();
          if (secTitle.includes(vTok)) {
            termScore *= 1.8;
          }
          docScores[docIdx] += termScore;
        }
      }
    }

    const indexedScores: { idx: number; score: number }[] = [];
    for (let i = 0; i < docScores.length; i++) {
      if (docScores[i] > 0) {
        indexedScores.push({ idx: i, score: docScores[i] });
      }
    }

    indexedScores.sort((a, b) => b.score - a.score);

    const results: RetrievedChunkTS[] = [];
    for (const item of indexedScores.slice(0, topK)) {
      const c = this.chunks[item.idx];
      const cit = `[${c.doc_id}] Section ${c.section_id}: ${c.section_title} (Lines ${c.line_start}-${c.line_end})`;
      results.push({
        chunk_id: c.chunk_id,
        doc_id: c.doc_id,
        doc_title: c.doc_title,
        section_id: c.section_id,
        section_title: c.section_title,
        line_start: c.line_start,
        line_end: c.line_end,
        text: c.text,
        score: Math.round(item.score * 1000) / 1000,
        citation: cit,
      });
    }

    return results;
  }

  public shouldAbstain(results: RetrievedChunkTS[]): boolean {
    if (results.length === 0) return true;
    return results[0].score < this.abstainThreshold;
  }
}
