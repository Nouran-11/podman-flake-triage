import json
from my_labels import LABELS

rs = json.load(open("extracted.json"))
ok = 0
print(f"{'#':<4}{'mine':<16}{'llm':<16}job")
print("-" * 68)
for i, r in enumerate(rs):
    llm = r.get("llm_category", "-")
    hit = LABELS[i] == llm
    ok += hit
    print(f"{'OK ' if hit else 'XX '}{i:<4}{LABELS[i]:<16}{llm:<16}{r['job_name'][:28]}")
print(f"\nagreement: {ok}/{len(rs)} ({100*ok/len(rs):.0f}%)")
