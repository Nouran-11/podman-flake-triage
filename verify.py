"""Fix the excerpt line count and check whether each excerpt
actually contains a test-failure marker."""
import json

MARKERS = ("not ok ", "[FAIL]", "--- FAIL:", "Summarizing", "FAIL!",
           "E: Failed to fetch", "level=fatal", "##[error]")

results = json.load(open("extracted.json"))
good = bad = 0

for i, r in enumerate(results):
    r["excerpt_lines"] = len(r["excerpt"].splitlines())
    hit = [m for m in MARKERS if m in r["excerpt"]]
    r["has_marker"] = bool(hit)
    if hit:
        good += 1
    else:
        bad += 1
        print(f"NO MARKER  #{i} {r['job_name']}")

json.dump(results, open("extracted.json", "w"), indent=2)

tin = sum(r["total_lines"] for r in results)
tout = sum(r["excerpt_lines"] for r in results)
print(f"\n{good}/{len(results)} excerpts contain a failure marker")
print(f"{tin} lines -> {tout} lines ({100*(1-tout/tin):.1f}% reduction)")
