"""
Inspect and analyze all 200 questions in data/official/questions_test.csv
against current SyncPulse pipeline.
"""
import sys
from pathlib import Path
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.pipeline import FrontlineCompanionPipeline

def analyze():
    df = pd.read_csv("data/official/questions_test.csv", encoding="utf-8")
    pipeline = FrontlineCompanionPipeline()

    records = []
    for idx, r in df.iterrows():
        qid = str(r["question_id"]).strip()
        qtext = str(r["question_text"]).strip()
        resp = pipeline.process_query(qtext)
        records.append({
            "idx": idx + 1,
            "qid": qid,
            "text": qtext,
            "type": resp.type,
            "cite": resp.primary_citation,
            "cites": resp.citations,
            "ans": resp.text[:100].replace("\n", " "),
        })

    with open("bench/test_set_analysis.txt", "w", encoding="utf-8") as out:
        out.write(f"Total Questions: {len(records)}\n")
        counts = {}
        for rec in records:
            counts[rec["type"]] = counts.get(rec["type"], 0) + 1
        out.write(f"Counts: {counts}\n\n--- DETAILED LISTING ---\n")
        for rec in records:
            out.write(f"[{rec['idx']:03d}] {rec['qid']} | {rec['type'].upper():8s} | {rec['cite']} | {rec['text']}\n")
    print("Done writing to bench/test_set_analysis.txt")

if __name__ == "__main__":
    analyze()
