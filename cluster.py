"""Group failures by normalised error signature, not test name.

Ports, hashes, container IDs and timestamps differ between runs and hide
the fact that many failures share one underlying cause.
"""
import json
import re
from collections import defaultdict

NOISE = [
    (r"\x1b\[[0-9;]*[a-zA-Z]|\[[0-9;]+m", ""),
    (r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b", "<IP>"),
    (r"sha256:[0-9a-f]{8,}", "sha256:<HASH>"),
    (r"\b[0-9a-f]{32,}\b", "<HASH>"),
    (r":\d{4,5}\b", ":<PORT>"),
    (r"\b\d{2}:\d{2}:\d{2}\.\d+\b", "<TIME>"),
    (r"\b20\d\d-\d\d-\d\dT[\d:.]+Z?\b", "<TS>"),
    (r"\bt\d+-[a-z0-9]{6,}\b", "<TESTID>"),
    (r"\bMacM1-\d+-worker\b", "<WORKER>"),
    (r"/tmp/[^\s\"']+", "<TMP>"),
    (r"\b\d+(\.\d+)?(ms|s|seconds)\b", "<DUR>"),
    (r"\b\d+\b", "N"),
]

SIGNAL = ("FAIL", "Error:", "error:", "not ok ", "[TIMEDOUT]",
          "failed", "fatal", "cannot", "ERROR")


def normalise(line):
    for pat, rep in NOISE:
        line = re.sub(pat, rep, line)
    return " ".join(line.split())[:110]


def signature(excerpt):
    best = None
    for line in excerpt.splitlines():
        s = line.strip()
        if len(s) < 15:
            continue
        if any(k in s for k in SIGNAL):
            if best is None or len(s) > len(best):
                best = s
    return normalise(best) if best else None


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
