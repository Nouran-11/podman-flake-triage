import json
import re

RULES = [
    ("network/apt-mirror", [
        r"Failed to fetch http://archive\.ubuntu\.com",
        r"Some index files failed to download",
    ]),
    ("network/vm-image-download", [
        r"failed to download.*\.qcow2\.zst",
        r"unexpected EOF",
    ]),
]


def classify(excerpt):
    for name, patterns in RULES:
        if any(re.search(p, excerpt) for p in patterns):
            return name
    return None


results = json.load(open("extracted.json"))
matched = 0

for r in results:
    label = classify(r["excerpt"])
    r["rule_category"] = label
    if label:
        matched += 1
    print(f"{label or 'UNMATCHED':<28} {r['job_name']}")

json.dump(results, open("extracted.json", "w"), indent=2)
print(f"\n{matched}/{len(results)} classified by rules "
      f"({100 * matched / len(results):.0f}%)")
print(f"{len(results) - matched} need the LLM")
