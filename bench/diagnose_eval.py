import json
import re
from pathlib import Path
import pandas as pd

def normalise(text: str) -> str:
    t = (text or "").lower()
    for a, b in (("–", "-"), ("—", "-"), ("−", "-"), ("≥", ">="),
                 ("≤", "<="), (" ", " "), ("°", " ")):
        t = t.replace(a, b)
    t = re.sub(r"(?<=\d)(?=[a-z])", " ", t)
    t = re.sub(r"(?<=\d)\s*-\s*(?=\d)", "-", t)
    return re.sub(r"\s+", " ", t).strip()

def fact_in_text(fact: str, text: str) -> bool:
    f = normalise(fact)
    if not f:
        return False
    return re.search(r"(?<![a-z0-9])" + re.escape(f) + r"(?![a-z0-9])", normalise(text)) is not None

def diagnose():
    truth_items = {
        json.loads(line)["question_id"]: json.loads(line)
        for line in Path("data/official/dev_truth.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    }
    pred_items = {
        json.loads(line)["question_id"]: json.loads(line)
        for line in Path("submission_dev/H5_answers.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    }
    qs = pd.read_csv("data/official/questions_dev.csv").set_index("question_id")["question_text"].to_dict()

    print("=" * 70)
    print("  DIAGNOSTIC ANALYSIS OF SUBMISSION_DEV")
    print("=" * 70)

    # 1. Refusal check
    print("\n--- REFUSAL MISMATCHES ---")
    for qid, t in truth_items.items():
        if t["must_escalate"]:
            continue
        p = pred_items[qid]
        if p["refused"] != t["out_of_scope"]:
            print(f"[{qid}] Truth out_of_scope={t['out_of_scope']}, Pred refused={p['refused']}")
            print(f"  Q: {qs[qid]}")
            print(f"  Pred text: {p['answer_text']}")

    # 2. Citation check (non out-of-scope)
    print("\n--- CITATION MISMATCHES ---")
    for qid, t in truth_items.items():
        if t["out_of_scope"]:
            continue
        p = pred_items[qid]
        pred_cites = [str(c).upper() for c in p["cited_section_ids"]]
        exp_cites = [str(c).upper() for c in t["expected_section_ids"]]
        match = any(c in exp_cites for c in pred_cites)
        if not match or len(pred_cites) > 2:
            print(f"[{qid}] Category={t['category']}")
            print(f"  Q: {qs[qid]}")
            print(f"  Expected: {exp_cites}")
            print(f"  Predicted: {pred_cites}")

    # 3. Key facts check
    print("\n--- KEY FACT MISMATCHES ---")
    for qid, t in truth_items.items():
        if t["out_of_scope"]:
            continue
        p = pred_items[qid]
        text_400 = p["answer_text"][:400]
        kfs = t.get("key_facts", [])
        kf_alts = t.get("key_fact_alternatives", [])
        missed_kfs = []
        for i, kf in enumerate(kfs):
            alts = kf_alts[i] if i < len(kf_alts) else [kf]
            found = any(fact_in_text(alt, text_400) for alt in alts)
            if not found:
                missed_kfs.append(alts)
        if missed_kfs:
            print(f"[{qid}] Missed Key Facts: {missed_kfs}")
            print(f"  Q: {qs[qid]}")
            print(f"  First 200 chars: {text_400[:200]}")
            print(f"  Expected answer: {t.get('expected_answer')}")

if __name__ == "__main__":
    diagnose()
