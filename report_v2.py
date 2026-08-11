"""Report recurring flakes in the format Podman maintainers already use:
occurrence count, date range, and the axes the failure spans.
"""
import json
import re
from collections import defaultdict

from signatures import signature

DISTROS = ["fedora-current", "fedora-prior", "fedora-rawhide",
           "debian-sid", "wsl", "hyperv", "applehv", "libkrun"]


def axes(job_names):
    """Which dimensions does this failure span?"""
    joined = " ".join(job_names)
    out = {}
    priv = [p for p in ("rootless", "root") if re.search(rf"\b{p}\b", joined)]
    if "rootless" in priv and "root" in priv:
        out["privilege"] = "both root and rootless"
    elif priv:
        out["privilege"] = priv[0]
    mode = [m for m in ("local", "remote") if re.search(rf"\b{m}\b", joined)]
    if len(mode) == 2:
        out["client"] = "both local and remote"
    elif mode:
        out["client"] = mode[0]
    found = [d for d in DISTROS if d in joined]
    if found:
        out["platform"] = ", ".join(found)
    return out


runs = json.load(open("cache/index.json"))
when = {e["run_id"]: e["created_at"][:10] for e in runs.values()}

rs = json.load(open("extracted.json"))
groups = defaultdict(list)
for r in rs:
    sig = signature(r["excerpt"])
    if sig:
        groups[sig].append(r)

recurring = {k: v for k, v in groups.items() if len(v) > 1}
print(f"# Recurring CI failures — {len(rs)} failures, "
      f"{len(groups)} signatures, {len(recurring)} recurring\n")

# Sort by distinct runs first: a failure recurring across many runs is
# more actionable than many jobs failing once together.
for sig, items in sorted(recurring.items(),
                        key=lambda x: (-len({i["run_id"] for i in x[1]}),
                                       -len(x[1]))):
    dates = sorted(when.get(i["run_id"], "?") for i in items)
    jobs = sorted({i["job_name"] for i in items})
    cat = {i.get("sig_category") for i in items}
    a = axes(jobs)

    print("---")
    print(f"**{sig[:95]}**\n")
    run_ids = {i["run_id"] for i in items}
    if len(run_ids) == 1:
        # All occurrences in ONE run: simultaneous failure across jobs,
        # which points at a regression rather than a recurring flake.
        print(f"Failed in {len(jobs)} job(s) of a SINGLE run on {dates[0]} "
              f"- simultaneous, not recurring.")
    else:
        span = dates[0] if dates[0] == dates[-1] else f"{dates[0]} and {dates[-1]}"
        print(f"Seen {len(items)} times across {len(run_ids)} runs "
              f"between {span}, in {len(jobs)} job(s).")
    for k, v in a.items():
        print(f"  {k}: {v}")
    print(f"  category: {', '.join(sorted(c for c in cat if c))}")
    print(f"  runs: {', '.join(str(x) for x in sorted(run_ids)[:5])}"
          + ("" if len(run_ids) <= 5 else f" (+{len(run_ids) - 5} more)"))
    print()

singles = len(groups) - len(recurring)
print(f"\n{singles} signatures seen only once (not shown).")
