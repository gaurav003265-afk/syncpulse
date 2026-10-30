import json
from pathlib import Path
import pandas as pd

def inspect_dev():
    truth_path = Path("data/official/dev_truth.jsonl")
    q_path = Path("data/official/questions_dev.csv")

    truth_items = [json.loads(line) for line in truth_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    qs = pd.read_csv(q_path).set_index("question_id")["question_text"].to_dict()

    must_esc = [t for t in truth_items if t["must_escalate"]]
    out_of_scope = [t for t in truth_items if t["out_of_scope"]]
    in_scope_norm = [t for t in truth_items if not t["must_escalate"] and not t["out_of_scope"]]

    print("=" * 70)
    print("  OFFICIAL DEV SET ANALYSIS (40 QUESTIONS)")
    print("=" * 70)
    print(f"Must Escalate (Emergency) : {len(must_esc)}")
    print(f"Out of Scope (Refusal)    : {len(out_of_scope)}")
    print(f"In-Scope Routine (Answer) : {len(in_scope_norm)}")
    print("-" * 70)

    print("\n--- MUST ESCALATE QUESTIONS (10 ITEMS) ---")
    for t in must_esc:
        qid = t["question_id"]
        qtext = qs.get(qid, "")
        secs = t.get("expected_section_ids", [])
        print(f"[{qid}] ({','.join(secs)})")
        print(f"  Q: {qtext}")
        print(f"  Notes: {t.get('notes')}")

    print("\n--- OUT OF SCOPE QUESTIONS (6 ITEMS) ---")
    for t in out_of_scope:
        qid = t["question_id"]
        qtext = qs.get(qid, "")
        print(f"[{qid}]")
        print(f"  Q: {qtext}")
        print(f"  Notes: {t.get('notes')}")

    print("\n--- IN-SCOPE ROUTINE SAMPLES (FIRST 5 OF 24) ---")
    for t in in_scope_norm[:5]:
        qid = t["question_id"]
        qtext = qs.get(qid, "")
        secs = t.get("expected_section_ids", [])
        print(f"[{qid}] ({','.join(secs)})")
        print(f"  Q: {qtext}")
        print(f"  Key facts: {t.get('key_facts')}")

if __name__ == "__main__":
    inspect_dev()
