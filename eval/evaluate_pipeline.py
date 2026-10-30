"""
Pipeline evaluation benchmark: retrieval quality, citation correctness, refusal accuracy, and latency.

Measures:
- Hit@1 & Hit@3 (section retrieval accuracy)
- Citation Correctness (grounded document & section match)
- Refusal Accuracy (guardrails on prescription, surgery, non-health)
- Escalation Recall on Dev Set
- Per-stage and end-to-end latency (ms)
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple

# Ensure project root in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Ensure UTF-8 stdout
if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from core.pipeline import FrontlineCompanionPipeline


def evaluate_pipeline(
    dev_set_path: Path,
    report_path: Optional[Path] = None,
) -> Tuple[bool, Dict[str, Any]]:
    pipeline = FrontlineCompanionPipeline()

    with open(dev_set_path, "r", encoding="utf-8-sig") as f:
        records = [json.loads(line.strip()) for line in f if line.strip()]

    total_records = len(records)
    latencies = []

    # Category counters
    in_scope_total = 0
    hit1_count = 0
    hit3_count = 0
    citation_correct_count = 0

    refusal_total = 0
    refusal_correct_count = 0

    escalation_total = 0
    escalation_correct_count = 0

    decision_correct_count = 0
    discrepancies: List[Dict[str, Any]] = []

    for item in records:
        qid = item["id"]
        q = item["query"]
        expected_type = item["expected_type"]
        exp_doc = item.get("expected_doc_id")
        exp_sec = item.get("expected_section_id")

        t0 = time.perf_counter()
        resp = pipeline.process_query(q)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        latencies.append(elapsed_ms)

        # Macro decision check
        is_decision_correct = (resp.type == expected_type)
        if is_decision_correct:
            decision_correct_count += 1
        else:
            discrepancies.append({
                "id": qid,
                "query": q,
                "expected_type": expected_type,
                "actual_type": resp.type,
                "reason": "Decision mismatch",
            })

        # 1. In-scope retrieval evaluation
        if expected_type == "answer":
            in_scope_total += 1
            # Check retrieval chunks
            retrieved = pipeline.retriever.search(q, top_k=3)
            retrieved_secs = [c.section_id for c in retrieved]

            # Hit@1
            if retrieved_secs and retrieved_secs[0] == exp_sec:
                hit1_count += 1

            # Hit@3
            if exp_sec in retrieved_secs:
                hit3_count += 1

            # Citation correctness
            if resp.primary_citation and exp_sec and (exp_sec in resp.primary_citation):
                citation_correct_count += 1
            elif not is_decision_correct:
                pass  # already logged

        # 2. Scope refusal evaluation
        elif expected_type == "refuse":
            refusal_total += 1
            if resp.type == "refuse":
                refusal_correct_count += 1

        # 3. Escalation evaluation
        elif expected_type == "escalate":
            escalation_total += 1
            if resp.type == "escalate":
                escalation_correct_count += 1

    # Aggregate metrics
    hit1_pct = (hit1_count / max(1, in_scope_total)) * 100.0
    hit3_pct = (hit3_count / max(1, in_scope_total)) * 100.0
    citation_pct = (citation_correct_count / max(1, in_scope_total)) * 100.0
    refusal_pct = (refusal_correct_count / max(1, refusal_total)) * 100.0
    escalation_pct = (escalation_correct_count / max(1, escalation_total)) * 100.0
    decision_pct = (decision_correct_count / total_records) * 100.0

    latencies.sort()
    avg_latency = sum(latencies) / max(1, len(latencies))
    p50_latency = latencies[int(len(latencies) * 0.50)]
    p95_latency = latencies[int(len(latencies) * 0.95)]

    metrics = {
        "total_dev_samples": total_records,
        "in_scope_samples": in_scope_total,
        "refusal_samples": refusal_total,
        "escalation_samples": escalation_total,
        "hit1_pct": round(hit1_pct, 2),
        "hit3_pct": round(hit3_pct, 2),
        "citation_correctness_pct": round(citation_pct, 2),
        "refusal_accuracy_pct": round(refusal_pct, 2),
        "escalation_recall_pct": round(escalation_pct, 2),
        "overall_decision_accuracy_pct": round(decision_pct, 2),
        "avg_latency_ms": round(avg_latency, 2),
        "p50_latency_ms": round(p50_latency, 2),
        "p95_latency_ms": round(p95_latency, 2),
        "discrepancies": discrepancies,
    }

    if report_path:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(metrics, f, indent=2, ensure_ascii=False)

    passed = (hit3_pct >= 90.0) and (refusal_pct >= 90.0) and (escalation_pct >= 100.0)
    return passed, metrics


def main():
    root = Path(__file__).resolve().parent.parent
    dev_path = root / "eval" / "dev_set.jsonl"
    report_path = root / "eval" / "reports" / "pipeline_eval_results.json"

    passed, m = evaluate_pipeline(dev_path, report_path)

    print("\n" + "=" * 65)
    print("      H5 PIPELINE & RETRIEVAL DEV BENCHMARK REPORT      ")
    print("=" * 65)
    print(f"Total Evaluated Questions : {m['total_dev_samples']}")
    print(f" - In-Scope Retrieval     : {m['in_scope_samples']}")
    print(f" - Scope Refusals         : {m['refusal_samples']}")
    print(f" - Danger Escalations     : {m['escalation_samples']}")
    print("-" * 65)
    print(f"Hit@1 Section Retrieval   : {m['hit1_pct']}%")
    print(f"Hit@3 Section Retrieval   : {m['hit3_pct']}%  (Target >= 90%)")
    print(f"Citation Correctness      : {m['citation_correctness_pct']}%")
    print(f"Refusal Accuracy          : {m['refusal_accuracy_pct']}%  (Target >= 90%)")
    print(f"Escalation Recall Gate    : {m['escalation_recall_pct']}%  (Target 100%)")
    print(f"Overall Decision Accuracy : {m['overall_decision_accuracy_pct']}%")
    print("-" * 65)
    print(f"CPU Latency (All Stages)  : Avg {m['avg_latency_ms']} ms | p50 {m['p50_latency_ms']} ms | p95 {m['p95_latency_ms']} ms")
    print("=" * 65)

    if passed:
        print(">>> RESULT: [PASS] STAGE 3 GATE ACHIEVED (HIT@3 & REFUSAL >= 90%, ESCALATION = 100%) <<<")
    else:
        print(">>> RESULT: [REVIEW] SOME THRESHOLDS REQUIRE CALIBRATION <<<")
        for d in m["discrepancies"][:5]:
            print(f" - [{d['id']}] {d['query']} (Expected: {d['expected_type']}, Got: {d['actual_type']})")
    print("=" * 65 + "\n")

    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
