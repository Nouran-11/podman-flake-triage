"""Group failures across runs and report what recurs."""
import json
from collections import Counter, defaultdict

rs = json.load(open("extracted.json"))

print(f"# Podman CI flake report — {len(rs)} failures\n")

# Which job families fail most
jobs = Counter(r["job_name"] for r in rs)
print("## Most frequent failing jobs\n")
for name, n in jobs.most_common(10):
    print(f"{n:>3}  {name}")

# Group by the failing test, not the job. Same test across
# different OS/privilege combinations is one flake, not many.
tests = defaultdict(list)
for r in rs:
    for line in r["excerpt"].splitlines():
        for m in ("[FAIL]", "[TIMEDOUT]", "not ok "):
            if m in line:
                tests[line.strip()[:100]].append(r["job_name"])
                break
        else:
            continue
        break

print("\n## Tests failing in more than one job\n")
repeat = {k: v for k, v in tests.items() if len(v) > 1}
for test, where in sorted(repeat.items(), key=lambda x: -len(x[1])):
    print(f"{len(where)}x  {test}")
    for w in sorted(set(where)):
        print(f"       {w}")

# Suite timeouts are a budget problem, not a test bug
timeouts = [r for r in rs if "Suite Timeout Elapsed" in r["excerpt"]]
print(f"\n## Suite timeouts: {len(timeouts)}\n")
for r in timeouts:
    print(f"  {r['job_name']}  {r['url']}")
