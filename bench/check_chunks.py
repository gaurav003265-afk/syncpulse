import json

with open('data/knowledge_pack/chunks.json', encoding='utf-8') as f:
    chunks = json.load(f)

print(f"Total chunks: {len(chunks)}")
for c in chunks:
    sid = c.get("section_id", "")
    if any(k in sid for k in ["HBNC", "ANC-1.1", "ANC-2.3", "IMM-1", "NUT-1"]):
        print(f"{c['chunk_id']} -> Section {sid}: {c['section_title']}")
