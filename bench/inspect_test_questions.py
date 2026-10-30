import sys
from pathlib import Path
import pandas as pd

if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.pipeline import FrontlineCompanionPipeline

def test_pipeline_on_test_set():
    q_path = Path("data/official/questions_test.csv")
    df = pd.read_csv(q_path)
    pipeline = FrontlineCompanionPipeline()

    types = {"escalate": [], "refuse": [], "answer": [], "abstain": []}
    for _, r in df.iterrows():
        qid = r["question_id"]
        qtext = r["question_text"]
        resp = pipeline.process_query(qtext)
        types[resp.type].append((qid, qtext, resp.primary_citation, resp.text[:120]))

    print("=" * 70)
    print("  TEST QUESTIONS PIPELINE SUMMARY (200 QUESTIONS)")
    print("=" * 70)
    print(f"Escalations : {len(types['escalate'])}")
    print(f"Refusals    : {len(types['refuse'])}")
    print(f"Answers     : {len(types['answer'])}")
    print(f"Abstentions : {len(types['abstain'])}")
    print("-" * 70)

    print("\nSAMPLE ESCALATIONS (FIRST 5):")
    for qid, qtext, cite, text in types["escalate"][:5]:
        print(f"[{qid}] ({cite}) {qtext[:60]}... -> {text[:80]}...")

    print("\nSAMPLE REFUSALS (FIRST 5):")
    for qid, qtext, cite, text in types["refuse"][:5]:
        print(f"[{qid}] ({cite}) {qtext[:60]}... -> {text[:80]}...")

    print("\nSAMPLE ANSWERS (FIRST 5):")
    for qid, qtext, cite, text in types["answer"][:5]:
        print(f"[{qid}] ({cite}) {qtext[:60]}... -> {text[:80]}...")

    if types["abstain"]:
        print("\nABSTENTIONS (SHOULD BE MINIMAL/ZERO):")
        for qid, qtext, cite, text in types["abstain"]:
            print(f"[{qid}] {qtext} -> {text}")

if __name__ == "__main__":
    test_pipeline_on_test_set()
