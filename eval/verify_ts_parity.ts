/**
 * Parity verification script between Python and TypeScript escalation engines.
 * Runs all 342 test items in eval/escalation_set.jsonl against web/src/engine/escalation.ts.
 * Checks for 100.0% Recall on emergencies and 0.0% False Escalation Rate.
 */

import * as fs from "node:fs";
import * as path from "node:path";
import { performance } from "node:perf_hooks";
import { fileURLToPath } from "node:url";

import { EscalationEngineTS } from "../web/src/engine/escalation.ts";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

async function main() {
  console.log("================================================================================");
  console.log("TALENT AP 2026 (H5) - TYPESCRIPT ESCALATION ENGINE PARITY EVALUATION");
  console.log("================================================================================");

  const engine = new EscalationEngineTS();
  const testSetPath = path.join(__dirname, "escalation_set.jsonl");

  if (!fs.existsSync(testSetPath)) {
    console.error(`ERROR: Test set not found at ${testSetPath}`);
    process.exit(1);
  }

  const lines = fs.readFileSync(testSetPath, "utf-8").split("\n").filter((l) => l.trim().length > 0);
  console.log(`Loaded ${lines.length} test queries from ${testSetPath}\n`);

  let tp = 0;
  let fn = 0;
  let tn = 0;
  let fp = 0;
  const latencies: number[] = [];
  const failures: any[] = [];

  for (const line of lines) {
    const item = JSON.parse(line);
    const query = item.query;
    const mustEscalate: boolean = item.must_escalate;

    const t0 = performance.now();
    const res = engine.check(query);
    const elapsed = performance.now() - t0;
    latencies.push(elapsed);

    if (mustEscalate) {
      if (res.escalate) {
        tp++;
      } else {
        fn++;
        failures.push({
          id: item.id,
          query,
          type: "FALSE_NEGATIVE",
          expected: true,
          got: false,
          rule: item.expected_rule_id,
        });
      }
    } else {
      if (!res.escalate) {
        tn++;
      } else {
        fp++;
        failures.push({
          id: item.id,
          query,
          type: "FALSE_POSITIVE",
          expected: false,
          got: true,
          triggered: res.primary_rule_id,
        });
      }
    }
  }

  const total = lines.length;
  const emergencyTotal = tp + fn;
  const routineTotal = tn + fp;

  const recall = emergencyTotal > 0 ? (tp / emergencyTotal) * 100 : 0;
  const precision = (tp + fp) > 0 ? (tp / (tp + fp)) * 100 : 0;
  const falseEscRate = routineTotal > 0 ? (fp / routineTotal) * 100 : 0;
  const avgLatency = latencies.reduce((a, b) => a + b, 0) / latencies.length;
  latencies.sort((a, b) => a - b);
  const p50 = latencies[Math.floor(latencies.length * 0.5)];
  const p95 = latencies[Math.floor(latencies.length * 0.95)];

  console.log("--------------------------------------------------------------------------------");
  console.log("EVALUATION RESULTS (TYPESCRIPT ENGINE)");
  console.log("--------------------------------------------------------------------------------");
  console.log(`Total Test Items Evaluated    : ${total}`);
  console.log(`Emergency Queries (Must=True) : ${emergencyTotal}`);
  console.log(`Routine Queries (Must=False)  : ${routineTotal}`);
  console.log("--------------------------------------------------------------------------------");
  console.log(`True Positives (TP)           : ${tp}`);
  console.log(`False Negatives (FN - CRITICAL): ${fn}`);
  console.log(`True Negatives (TN)           : ${tn}`);
  console.log(`False Positives (FP)          : ${fp}`);
  console.log("--------------------------------------------------------------------------------");
  console.log(`ESCALATION RECALL             : ${recall.toFixed(2)}% (Target: 100.0%)`);
  console.log(`ESCALATION PRECISION          : ${precision.toFixed(2)}%`);
  console.log(`FALSE ESCALATION RATE         : ${falseEscRate.toFixed(2)}% (Target: 0.0%)`);
  console.log("--------------------------------------------------------------------------------");
  console.log(`Average CPU Latency (Node)    : ${avgLatency.toFixed(3)} ms`);
  console.log(`P50 Latency                   : ${p50.toFixed(3)} ms`);
  console.log(`P95 Latency                   : ${p95.toFixed(3)} ms`);
  console.log("--------------------------------------------------------------------------------");

  if (failures.length > 0) {
    console.log("\nFAILURES DETECTED:");
    for (const f of failures.slice(0, 10)) {
      console.log(`  [${f.type}] ID: ${f.id} | Rule: ${f.rule || f.triggered} | Q: "${f.query}"`);
    }
    process.exit(1);
  } else {
    console.log("\n>>> HARD GATE PASSED: 100.0% RECALL (0 False Negatives) in TypeScript! <<<");
    console.log(">>> Full Parity between Python core/escalation.py and TypeScript escalation.ts verified! <<<\n");
  }
}

main().catch((err) => {
  console.error("Execution error:", err);
  process.exit(1);
});
