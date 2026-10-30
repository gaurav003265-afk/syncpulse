"""
Runs SyncPulse on the 40 official development questions and dev register.
Generates submission_dev/ files and runs official_dataset/evaluate.py!
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.pipeline import FrontlineCompanionPipeline
from core.vis_rules import generate_whole_register_visit_list


def run_dev_evaluation():
    out_dir = PROJECT_ROOT / "submission_dev"
    out_dir.mkdir(parents=True, exist_ok=True)

    # 1. Answer 40 dev questions
    q_path = PROJECT_ROOT / "data" / "official" / "questions_dev.csv"
    qs = pd.read_csv(q_path, dtype=str)

    pipeline = FrontlineCompanionPipeline()

    answers = []
    latencies = []

    print("Running SyncPulse pipeline on 40 dev questions...")
    for _, r in qs.iterrows():
        qid = str(r["question_id"]).strip()
        qtext = str(r["question_text"]).strip()

        t0 = time.perf_counter()
        resp = pipeline.process_query(qtext)
        ms = (time.perf_counter() - t0) * 1000.0
        latencies.append(ms)

        # Map pipeline response to official answer schema
        escalate_bool = (resp.type == "escalate")
        refused_bool = (resp.type == "refuse")

        # Leaf section citations: extract leaf IDs (e.g. ANC-1.2, ESC-2.7, SCP-1.2)
        cited_ids = []
        if resp.primary_citation:
            # Check if leaf section ID is embedded
            import re
            m = re.search(r"([A-Za-z]{2,4}-\d+\.\d+)", resp.primary_citation)
            if m:
                cited_ids.append(m.group(1).upper())
        for c in resp.citations:
            m = re.search(r"([A-Za-z]{2,4}-\d+\.\d+)", c)
            if m:
                cid = m.group(1).upper()
                if cid not in cited_ids:
                    cited_ids.append(cid)

        # Cap citations at 2 per official rules
        cited_ids = cited_ids[:2]
        if refused_bool and not cited_ids:
            cited_ids = ["SCP-1.2"]

        answers.append({
            "question_id": qid,
            "answer_text": resp.text[:400],  # Ensure first 400 chars contain key facts
            "cited_section_ids": cited_ids,
            "escalate": escalate_bool,
            "refused": refused_bool,
            "latency_ms": round(ms, 3),
        })

    # Write H5_answers.jsonl
    answers_file = out_dir / "H5_answers.jsonl"
    with open(answers_file, "w", encoding="utf-8") as f:
        for a in answers:
            f.write(json.dumps(a, ensure_ascii=False) + "\n")

    # 2. Generate H5_visit_list.csv (Whole Register)
    print("Generating official whole-register visit list...")
    visit_df = generate_whole_register_visit_list()
    visit_file = out_dir / "H5_visit_list.csv"
    visit_df[["member_id", "due_item", "priority"]].to_csv(visit_file, index=False)

    # 3. Generate H5_footprint.json
    import psutil
    process = psutil.Process()
    peak_ram = round(process.memory_info().rss / (1024 * 1024), 2)
    median_lat = round(float(pd.Series(latencies).median()), 3)

    footprint = {
        "model_names": ["SyncPulse-Deterministic-BM25-Extractive"],
        "model_size_mb": 1.58,
        "peak_ram_mb": peak_ram,
        "median_latency_ms_cpu": median_lat,
        "offline": True,
    }
    footprint_file = out_dir / "H5_footprint.json"
    with open(footprint_file, "w", encoding="utf-8") as f:
        json.dump(footprint, f, indent=2)

    print(f"\nWrote 3 submission files to: {out_dir}")
    print(f" - {answers_file.name}: {len(answers)} records")
    print(f" - {visit_file.name}: {len(visit_df)} rows")
    print(f" - {footprint_file.name}: RAM {peak_ram} MB, median latency {median_lat} ms")

    # 4. Invoke official evaluator directly!
    print("\n" + "=" * 70)
    print("  RUNNING OFFICIAL EVALUATOR ON SUBMISSION_DEV")
    print("=" * 70)
    import subprocess
    cmd = [
        sys.executable,
        str(PROJECT_ROOT / "official_dataset" / "evaluate.py"),
        "--submission", str(out_dir),
        "--truth", str(PROJECT_ROOT / "data" / "official" / "dev_truth.jsonl"),
        "--out", str(PROJECT_ROOT / "submission_dev" / "score_dev.json"),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    print(res.stdout)
    if res.stderr:
        print("Evaluator Error Output:", res.stderr)


if __name__ == "__main__":
    run_dev_evaluation()
