import json
with open('data/escalation_rules.json', encoding='utf-8') as f:
    d = json.load(f)
for r in d['rules']:
    print(f"{r['rule_id']}: {r['corpus_citation']} | {r['title']}")
