import json

with open('data/official/dev_truth.jsonl', encoding='utf-8') as f:
    for line in f:
        d = json.loads(line)
        if d.get('must_escalate'):
            print(f"[ESCALATE] {d['question_id']}: {d['expected_section_ids']} | {d['key_facts']}")
        elif d.get('out_of_scope'):
            print(f"[REFUSE]   {d['question_id']}: {d['expected_section_ids']} | {d['key_facts']}")
