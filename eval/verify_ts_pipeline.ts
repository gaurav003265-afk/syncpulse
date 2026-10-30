/**
 * Evaluates the full TypeScript pipeline on eval/dev_set.jsonl (96 queries).
 * Tests retrieval quality (Hit@1, Hit@3), citation correctness, scope refusal, and latency.
 */

import * as fs from "node:fs";
import * as path from "node:path";
import { performance } from "node:perf_hooks";
import { fileURLToPath } from "node:url";

import { PipelineTS } from "../web/src/engine/pipeline.ts";
import { BM25RetrieverTS } from "../web/src/engine/retrieve.ts";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

async function main() {
  console.log("================================================================================");
  console.log("TALENT AP 2026 (H5) - FULL TYPESCRIPT PIPELINE EVALUATION");
  console.log("================================================================================");

  const pipeline = new PipelineTS();
  const retriever = new BM25RetrieverTS();
  const devSetPath = path.join(__dirname, "dev_set.jsonl");

  if (!fs.existsSync(devSetPath)) {
    console.error(`ERROR: Dev set not found at ${devSetPath}`);
    process.exit(1);
  }

  const lines = fs.readFileSync(devSetPath, "utf-8").split("\n").filter((l) => l.trim().length > 0);
  console.log(`Loaded ${lines.length} queries from ${devSetPath}\n`);

  let decisionCorrect = 0;
  let inScopeTotal = 0;
  let hit1Count = 0;
  let hit3Count = 0;
  let citCorrect = 0;

  let refusalTotal = 0;
  let refusalCorrect = 0;

  let emergencyTotal = 0;
  let emergencyCorrect = 0;

  const latencies: number[] = [];
  const discrepancies: any[] = [];

  for (const line of lines) {
    const item = JSON.parse(line);
    const query = item.query;
    const expectedType: string = item.expected_type;
    const expDoc: string = item.expected_doc_id;
    const expSec: string = item.expected_section_id;

    const t0 = performance.now();
    const res = pipeline.processQuery(query);
    const elapsed = performance.now() - t0;
    latencies.push(elapsed);

    if (res.type === expectedType) {
      decisionCorrect++;
    } else {
      discrepancies.push({
        id: item.id,
        query,
        expected: expectedType,
        got: res.type,
      });
    }

    if (expectedType === "answer") {
      inScopeTotal++;
      const retrieved = retriever.search(query, 3);
      const retSecs = retrieved.map((c) => c.section_id);

      if (retSecs.length > 0 && retSecs[0] === expSec) {
        hit1Count++;
      }
      if (retSecs.includes(expSec)) {
        hit3Count++;
      }
      if (res.primary_citation && res.primary_citation.includes(expSec)) {
        citCorrect++;
      }
    } else if (expectedType === "refuse") {
      refusalTotal++;
      if (res.type === "refuse") refusalCorrect++;
    } else if (expectedType === "escalate") {
      emergencyTotal++;
      if (res.type === "escalate") emergencyCorrect++;
    }
  }

  const total = lines.length;
  const decisionAcc = (decisionCorrect / total) * 100;
  const hit1Acc = inScopeTotal > 0 ? (hit1Count / inScopeTotal) * 100 : 0;
  const hit3Acc = inScopeTotal > 0 ? (hit3Count / inScopeTotal) * 100 : 0;
  const citAcc = inScopeTotal > 0 ? (citCorrect / inScopeTotal) * 100 : 0;
  const refAcc = refusalTotal > 0 ? (refusalCorrect / refusalTotal) * 100 : 0;
  const emAcc = emergencyTotal > 0 ? (emergencyCorrect / emergencyTotal) * 100 : 0;

  const avgLatency = latencies.reduce((a, b) => a + b, 0) / latencies.length;
  latencies.sort((a, b) => a - b);
  const p50 = latencies[Math.floor(latencies.length * 0.5)];
  const p95 = latencies[Math.floor(latencies.length * 0.95)];

  console.log("--------------------------------------------------------------------------------");
  console.log("PIPELINE PERFORMANCE RESULTS (TYPESCRIPT)");
  console.log("--------------------------------------------------------------------------------");
  console.log(`Total Queries Evaluated       : ${total}`);
  console.log(`Overall Decision Accuracy     : ${decisionAcc.toFixed(2)}% (${decisionCorrect}/${total})`);
  console.log(`Emergency Escalation Accuracy : ${emAcc.toFixed(2)}% (${emergencyCorrect}/${emergencyTotal})`);
  console.log(`Scope Refusal Accuracy        : ${refAcc.toFixed(2)}% (${refusalCorrect}/${refusalTotal})`);
  console.log(`Hit@1 Section Retrieval       : ${hit1Acc.toFixed(2)}% (${hit1Count}/${inScopeTotal})`);
  console.log(`Hit@3 Section Retrieval       : ${hit3Acc.toFixed(2)}% (${hit3Count}/${inScopeTotal})`);
  console.log(`Citation Correctness (In-Scope): ${citAcc.toFixed(2)}% (${citCorrect}/${inScopeTotal})`);
  console.log("--------------------------------------------------------------------------------");
  console.log(`Average CPU Latency (Node)    : ${avgLatency.toFixed(3)} ms`);
  console.log(`P50 Latency                   : ${p50.toFixed(3)} ms`);
  console.log(`P95 Latency                   : ${p95.toFixed(3)} ms`);
  console.log("--------------------------------------------------------------------------------\n");

  if (discrepancies.length > 0) {
    console.log("DISCREPANCIES:");
    for (const d of discrepancies) {
      console.log(`  [${d.id}] Expected: ${d.expected} | Got: ${d.got} | Q: "${d.query}"`);
    }
  }
}

main().catch((err) => {
  console.error("Evaluation error:", err);
  process.exit(1);
});
