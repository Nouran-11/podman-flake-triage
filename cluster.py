"""Group failures by normalised error signature, not test name.

Ports, hashes, container IDs and timestamps differ between runs and hide
the fact that many failures share one underlying cause.
"""
import json
from collections import defaultdict

from signatures import normalise, signature


rs = json.load(open("extracted.json"))
groups = defaultdict(list)
for r in rs:
    sig = signature(r["excerpt"])
    if sig:
        groups[sig].append(r)

print(f"# {len(rs)} failures -> {len(groups)} distinct signatures\n")
print("## Recurring signatures (2+ occurrences)\n")
for sig, items in sorted(groups.items(), key=lambda x: -len(x[1])):
    if len(items) < 2:
        continue
    jobs = sorted({i["job_name"] for i in items})
    cats = sorted({i.get("llm_v2_category") for i in items if i.get("llm_v2_category")})
    print(f"{len(items):>3}x  {sig}")
    print(f"      category: {', '.join(cats)}")
    print(f"      {len(jobs)} job(s): {', '.join(j[:32] for j in jobs[:6])}")
    print()
print(f"{sum(1 for v in groups.values() if len(v) == 1)} signatures occurred once.")
