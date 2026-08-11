"""Classify each distinct failure signature once, not each occurrence.

Two wins over per-occurrence classification:
  - consistency by construction: identical evidence cannot get two verdicts
  - fewer LLM calls (one per signature instead of one per failure)
"""
import json
from collections import defaultdict

from llm_categorize_v2 import ask
from signatures import signature

rs = json.load(open("extracted.json"))

groups = defaultdict(list)
unsigned = []
for r in rs:
    sig = signature(r["excerpt"])
    r["signature"] = sig
    (groups[sig] if sig else unsigned).append(r)

print(f"{len(rs)} failures -> {len(groups)} signatures "
      f"({len(unsigned)} without a usable signature)\n")

for n, (sig, items) in enumerate(sorted(groups.items(),
                                        key=lambda x: -len(x[1])), 1):
    rep = max(items, key=lambda r: len(r["excerpt"]))
    v = ask(rep["job_name"], rep["excerpt"])
    cat = v.get("category")
    for r in items:
        r["sig_category"] = cat
        r["sig_evidence"] = v.get("evidence")
        r["sig_reason"] = v.get("reason")
    print(f"[{n}/{len(groups)}] {cat:<15} x{len(items):<3} {sig[:70]}")

for r in unsigned:
    r["sig_category"] = r.get("llm_v2_category")
    r["sig_reason"] = "no signature; kept per-occurrence result"

json.dump(rs, open("extracted.json", "w"), indent=2)

calls_before, calls_after = len(rs), len(groups)
print(f"\nLLM calls: {calls_before} -> {calls_after} "
      f"({100 * (1 - calls_after / calls_before):.0f}% fewer)")

# How often did per-occurrence classification contradict itself?
split = sum(1 for items in groups.values()
            if len({i.get("llm_v2_category") for i in items}) > 1)
print(f"{split} signatures had inconsistent per-occurrence labels; "
      f"per-signature classification removes this by construction.")
