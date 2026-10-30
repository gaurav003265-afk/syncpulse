"""
Evaluates core/vis_rules.py against the official development truth:
- data/official/dev_truth_visit_list.csv (39 truth rows)
- data/official/dev_truth_visit_scope.csv (229 dev members)

Computes F1, Priority Accuracy, and Visit List Score exactly as evaluate.py does!
"""

import sys
from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.vis_rules import generate_whole_register_visit_list

def eval_dev_visit_list():
    pred_df = generate_whole_register_visit_list()
    scope_df = pd.read_csv("data/official/dev_truth_visit_scope.csv", dtype=str)
    truth_df = pd.read_csv("data/official/dev_truth_visit_list.csv", dtype=str)

    scope_members = set(scope_df["member_id"].str.strip())
    
    # Filter predictions to members in dev truth scope
    pred_in_scope = pred_df[pred_df["member_id"].isin(scope_members)].copy()
    pred_in_scope["priority"] = pred_in_scope["priority"].astype(int)
    truth_df["priority"] = truth_df["priority"].astype(int)

    # Compare pairs
    pred_pairs = set(zip(pred_in_scope["member_id"].str.strip(), pred_in_scope["due_item"].str.strip().str.upper()))
    truth_pairs = set(zip(truth_df["member_id"].str.strip(), truth_df["due_item"].str.strip().str.upper()))

    tp_pairs = pred_pairs.intersection(truth_pairs)
    fp_pairs = pred_pairs - truth_pairs
    fn_pairs = truth_pairs - pred_pairs

    precision = len(tp_pairs) / max(1, len(pred_pairs))
    recall = len(tp_pairs) / max(1, len(truth_pairs))
    f1 = 2 * precision * recall / max(1e-9, precision + recall)

    # Priority accuracy = (truth rows predicted with correct priority) / max(len(truth), len(pred_in_scope))
    pred_prio_map = dict(zip(zip(pred_in_scope["member_id"].str.strip(), pred_in_scope["due_item"].str.strip().str.upper()), pred_in_scope["priority"]))
    truth_prio_map = dict(zip(zip(truth_df["member_id"].str.strip(), truth_df["due_item"].str.strip().str.upper()), truth_df["priority"]))

    correct_prio = 0
    prio_mismatches = []
    for pair, t_prio in truth_prio_map.items():
        if pair in pred_prio_map:
            p_prio = pred_prio_map[pair]
            if p_prio == t_prio:
                correct_prio += 1
            else:
                prio_mismatches.append((pair, f"Truth: {t_prio}, Pred: {p_prio}"))

    denom = max(len(truth_df), len(pred_in_scope))
    prio_accuracy = correct_prio / denom
    visit_score = 0.6 * f1 + 0.4 * prio_accuracy

    print("=" * 60)
    print("  VIS RULES BENCHMARK ON DEV TRUTH (229 MEMBERS)")
    print("=" * 60)
    print(f"Total Predicted Rows (Whole Register): {len(pred_df)}")
    print(f"Predicted in Dev Scope               : {len(pred_in_scope)}")
    print(f"Truth in Dev Scope                   : {len(truth_df)}")
    print(f"True Positive (Member, Item) Pairs   : {len(tp_pairs)} / {len(truth_df)}")
    print(f"False Positive Pairs (Extra)         : {len(fp_pairs)}")
    print(f"False Negative Pairs (Missing)       : {len(fn_pairs)}")
    print(f"Precision                            : {precision * 100:.2f}%")
    print(f"Recall                               : {recall * 100:.2f}%")
    print(f"F1 Score                             : {f1 * 100:.2f}%")
    print(f"Correct Priority Matches             : {correct_prio} / {len(truth_df)}")
    print(f"Priority Accuracy                    : {prio_accuracy * 100:.2f}%")
    print("-" * 60)
    print(f"VISIT LIST SCORE (0.6*F1 + 0.4*Prio) : {visit_score:.4f} (Baseline was: 0.6154)")
    print("=" * 60)

    if fn_pairs:
        print("\nMissing Pairs (FN):")
        for p in sorted(list(fn_pairs)):
            # Lookup truth row details
            t_row = truth_df[(truth_df["member_id"] == p[0]) & (truth_df["due_item"].str.upper() == p[1])].iloc[0]
            print(f" - {p[0]} {p[1]}: Priority {t_row['priority']}, Status {t_row.get('status')}, Due {t_row.get('due_date')}")

    if fp_pairs:
        print("\nExtra Pairs (FP):")
        for p in sorted(list(fp_pairs)):
            p_row = pred_in_scope[(pred_in_scope["member_id"] == p[0]) & (pred_in_scope["due_item"].str.upper() == p[1])].iloc[0]
            print(f" - {p[0]} {p[1]}: Priority {p_row['priority']}, Status {p_row.get('status')}, Due {p_row.get('due_date')}")

    if prio_mismatches:
        print("\nPriority Mismatches:")
        for pair, diff in prio_mismatches:
            print(f" - {pair}: {diff}")

if __name__ == "__main__":
    eval_dev_visit_list()
