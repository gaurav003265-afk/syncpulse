import sys

sys.stdout.reconfigure(encoding="utf-8")

with open('bench/test_set_analysis.txt', encoding='utf-8') as f:
    lines = f.readlines()

print("ALL 45 ESCALATIONS:")
for line in lines:
    if " | ESCALATE " in line:
        print(line.strip())
