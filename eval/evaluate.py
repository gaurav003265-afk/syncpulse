"""
Standalone evaluation harness for emergency escalation detection.

Measures:
- Escalation Recall (Hard Gate: 100.0% required)
- False Escalation Rate (FER)
- Precision, Specificity, F1-Score
- Per-query latency (ms)

Robust to:
- JSONL, JSON array, and CSV formats
- UTF-8 with and without BOM
- Missing or alternative column names ('query', 'question', 'text', 'must_escalate', 'escalate')
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple

# Ensure project root is in sys.path regardless of execution method
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Ensure stdout and stderr use UTF-8 encoding across Windows PowerShell/CMD
if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from core.escalation import EscalationEngine


def load_dataset(file_path: Path) -> List[Dict[str, Any]]:
    """
    Robust loader supporting JSONL, JSON array, and CSV files,
    handling UTF-8 BOM and column variations.
    """
    if not file_path.exists():
        raise FileNotFoundError(f"Evaluation file not found: {file_path}")

    items = []
    # Use utf-8-sig to automatically handle UTF-8 with or without BOM
    suffix = file_path.suffix.lower()

    if suffix == ".jsonl":
        with open(file_path, "r", encoding="utf-8-sig") as f:
            for line_idx, line in enumerate(f, start=1):
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    items.append(standardize_record(data, line_idx))
                except json.JSONDecodeError as e:
                    print(f"Warning: JSON decode error at line {line_idx}: {e}")

    elif suffix == ".json":
        with open(file_path, "r", encoding="utf-8-sig") as f:
            raw_data = json.load(f)
            if isinstance(raw_data, list):
                for idx, record in enumerate(raw_data, start=1):
                    items.append(standardize_record(record, idx))
            elif isinstance(raw_data, dict):
                # Could be a wrapped dict with key 'questions' or 'items'
                for k in ["questions", "items", "records", "data"]:
                    if k in raw_data and isinstance(raw_data[k], list):
                        for idx, record in enumerate(raw_data[k], start=1):
                            items.append(standardize_record(record, idx))
                        break

    elif suffix == ".csv":
        with open(file_path, "r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            for idx, row in enumerate(reader, start=1):
                items.append(standardize_record(row, idx))

    else:
        raise ValueError(f"Unsupported file format: {suffix}. Must be .jsonl, .json, or .csv")

    if not items:
        raise ValueError(f"No valid records loaded from {file_path}")

    return items


def standardize_record(record: Dict[str, Any], index: int) -> Dict[str, Any]:
    """Standardizes input keys across diverse organizer formats."""
    # Find query text
    query = ""
    for q_key in ["query", "question", "text", "prompt", "input"]:
        if q_key in record and record[q_key]:
            query = str(record[q_key]).strip()
            break

    # Find escalation label (defaults to None if unlabeled, e.g. organizer blind set)
    must_escalate = None
    for e_key in ["must_escalate", "escalate", "is_emergency", "danger_sign", "requires_escalation"]:
        if e_key in record:
            val = record[e_key]
            if isinstance(val, bool):
                must_escalate = val
            elif isinstance(val, (int, float)):
                must_escalate = bool(val)
            elif isinstance(val, str):
                must_escalate = val.lower().strip() in ("true", "1", "yes", "y", "t", "emergency")
            break

    record_id = record.get("id", f"REC-{index:04d}")
    expected_rule = record.get("expected_rule_id", None)

    return {
        "id": record_id,
        "query": query,
        "must_escalate": must_escalate,
        "expected_rule_id": expected_rule,
        "raw": record,
    }


def evaluate(
    test_file: Path,
    rules_file: Optional[Path] = None,
    output_report: Optional[Path] = None,
) -> Tuple[bool, Dict[str, Any]]:
    """
    Runs the evaluation suite on the specified test dataset.
    Returns (gate_passed: bool, metrics: dict).
    """
    engine = EscalationEngine(str(rules_file) if rules_file else None)
    records = load_dataset(test_file)

    tp = 0  # Expected escalate=True, Got escalate=True
    fn = 0  # Expected escalate=True, Got escalate=False (CRITICAL FAIL)
    tn = 0  # Expected escalate=False, Got escalate=False
    fp = 0  # Expected escalate=False, Got escalate=True

    unlabeled_count = 0
    failures: List[Dict[str, Any]] = []
    false_positives: List[Dict[str, Any]] = []
    latencies: List[float] = []

    for item in records:
        q = item["query"]
        ground_truth = item["must_escalate"]

        t0 = time.perf_counter()
        result = engine.check(q)
        t1 = time.perf_counter()
        latencies.append((t1 - t0) * 1000.0)  # ms

        predicted = result.escalate

        if ground_truth is None:
            unlabeled_count += 1
            continue

        if ground_truth and predicted:
            tp += 1
        elif ground_truth and not predicted:
            fn += 1
            failures.append({
                "id": item["id"],
                "query": q,
                "expected_rule": item["expected_rule_id"],
                "engine_reason": result.trigger_reason,
            })
        elif not ground_truth and not predicted:
            tn += 1
        elif not ground_truth and predicted:
            fp += 1
            false_positives.append({
                "id": item["id"],
                "query": q,
                "triggered_rule": result.primary_rule_id,
                "trigger_reason": result.trigger_reason,
            })

    total_labeled = tp + fn + tn + fp
    total_emergency = tp + fn
    total_routine = tn + fp

    recall = (tp / total_emergency * 100.0) if total_emergency > 0 else 100.0
    fer = (fp / total_routine * 100.0) if total_routine > 0 else 0.0
    precision = (tp / (tp + fp) * 100.0) if (tp + fp) > 0 else 0.0
    specificity = (tn / total_routine * 100.0) if total_routine > 0 else 100.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0

    avg_latency = sum(latencies) / max(1, len(latencies))
    latencies.sort()
    p50_latency = latencies[int(len(latencies) * 0.50)]
    p95_latency = latencies[int(len(latencies) * 0.95)]

    # Hard gate check: 100% recall on danger signs
    gate_passed = (fn == 0) and (recall >= 100.0)

    metrics = {
        "dataset_file": str(test_file.name),
        "total_records": len(records),
        "total_labeled": total_labeled,
        "unlabeled_records": unlabeled_count,
        "emergency_samples": total_emergency,
        "routine_samples": total_routine,
        "true_positives": tp,
        "false_negatives": fn,
        "true_negatives": tn,
        "false_positives": fp,
        "escalation_recall_pct": round(recall, 2),
        "false_escalation_rate_pct": round(fer, 2),
        "precision_pct": round(precision, 2),
        "specificity_pct": round(specificity, 2),
        "f1_score": round(f1, 4),
        "avg_latency_ms": round(avg_latency, 3),
        "p50_latency_ms": round(p50_latency, 3),
        "p95_latency_ms": round(p95_latency, 3),
        "gate_passed": gate_passed,
        "failures": failures,
        "false_positives": false_positives,
    }

    if output_report:
        output_report.parent.mkdir(parents=True, exist_ok=True)
        with open(output_report, "w", encoding="utf-8") as f:
            json.dump(metrics, f, indent=2, ensure_ascii=False)

    return gate_passed, metrics


def print_summary(metrics: Dict[str, Any]):
    print("\n" + "=" * 65)
    print("      H5 ESCALATION EVALUATION BENCHMARK REPORT      ")
    print("=" * 65)
    print(f"Dataset File          : {metrics['dataset_file']}")
    print(f"Total Evaluated Items : {metrics['total_labeled']} (Emergency: {metrics['emergency_samples']}, Routine: {metrics['routine_samples']})")
    print(f"Latency (CPU proxy)   : Avg {metrics['avg_latency_ms']} ms | p50 {metrics['p50_latency_ms']} ms | p95 {metrics['p95_latency_ms']} ms")
    print("-" * 65)
    print(f"True Positives (TP)   : {metrics['true_positives']}")
    print(f"False Negatives (FN)  : {metrics['false_negatives']}   <-- [MUST BE 0 FOR 100% RECALL GATE]")
    print(f"True Negatives (TN)   : {metrics['true_negatives']}")
    print(f"False Positives (FP)  : {metrics['false_positives']}")
    print("-" * 65)
    print(f"ESCALATION RECALL     : {metrics['escalation_recall_pct']}%  (Target: 100.0%)")
    print(f"False Escalation Rate : {metrics['false_escalation_rate_pct']}%")
    print(f"Precision             : {metrics['precision_pct']}%")
    print(f"Specificity           : {metrics['specificity_pct']}%")
    print(f"F1 Score              : {metrics['f1_score']}")
    print("=" * 65)

    if metrics["gate_passed"]:
        print(">>> RESULT: [PASS] CRITICAL SAFETY GATE ACHIEVED (100% RECALL) <<<")
    else:
        print(">>> RESULT: [FAIL] RECALL GATE MISSED! DANGER SIGNS UNDETECTED! <<<")
        print(f"Total Missed Danger Signs: {len(metrics['failures'])}")
        for fail in metrics["failures"][:5]:
            print(f" - [{fail['id']}] {fail['query']} (Expected: {fail['expected_rule']})")
    print("=" * 65 + "\n")


def main():
    parser = argparse.ArgumentParser(description="Evaluate escalation recall and precision")
    parser.add_argument("--test-file", type=str, default="eval/escalation_set.jsonl", help="Path to evaluation dataset")
    parser.add_argument("--rules-file", type=str, default=None, help="Custom rules JSON path")
    parser.add_argument("--report", type=str, default="eval/reports/escalation_eval_results.json", help="Path to write JSON report")
    args = parser.parse_args()

    test_path = Path(args.test_file)
    rules_path = Path(args.rules_file) if args.rules_file else None
    report_path = Path(args.report) if args.report else None

    passed, metrics = evaluate(test_path, rules_path, report_path)
    print_summary(metrics)

    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
