import json
import sys
from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.escalation import EscalationEngine

def test_current_escalation():
    engine = EscalationEngine()
    truth_items = [json.loads(line) for line in Path("data/official/dev_truth.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    qs = pd.read_csv("data/official/questions_dev.csv").set_index("question_id")["question_text"].to_dict()

    tp, fp, fn, tn = [], [], [], []

    for t in truth_items:
        qid = t["question_id"]
        qtext = qs.get(qid, "")
        must_esc = t["must_escalate"]
        res = engine.check(qtext)
        pred_esc = res.escalate

        if must_esc and pred_esc:
            tp.append(qid)
        elif not must_esc and pred_esc:
            fp.append((qid, qtext, res.matched_rules))
        elif must_esc and not pred_esc:
            fn.append((qid, qtext))
        else:
            tn.append(qid)

    print("=" * 60)
    print("  CURRENT ESCALATION ENGINE ON DEV SET (40 QS)")
    print("=" * 60)
    print(f"TP: {len(tp)} / 10 must-escalate")
    print(f"FN: {len(fn)} (Must be 0!)")
    print(f"FP: {len(fp)} / 30 non-danger (Must be <= 6 for <= 20% rate!)")
    print(f"TN: {len(tn)}")
    recall = len(tp) / (len(tp) + len(fn)) if (tp or fn) else 0.0
    fer = len(fp) / (len(fp) + len(tn)) if (fp or tn) else 0.0
    print(f"Recall: {recall * 100:.1f}%")
    print(f"False Escalation Rate: {fer * 100:.1f}%")
    print(f"Gate Pass? {'YES' if recall == 1.0 and fer <= 0.20 else 'FAIL'}")
    print("=" * 60)

    if fn:
        print("\nMISSED EMERGENCIES (FN):")
        for qid, qtext in fn:
            print(f" - [{qid}]: {qtext}")

    if fp:
        print("\nFALSE ALARMS (FP):")
        for qid, qtext, rules in fp:
            print(f" - [{qid}]: {qtext}")
            print(f"   Matched: {[r.rule_id for r in rules]}")

if __name__ == "__main__":
    test_current_escalation()
