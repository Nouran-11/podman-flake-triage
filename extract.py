import json
import re
import zipfile

# Windows/PowerShell logs are full of colour escape codes, which make
# lines unquotable for the LLM. Strip them at extraction time.
ANSI = re.compile(r'\x1b\[[0-9;]*[a-zA-Z]|\[[0-9;]+m|\[0m')
from pathlib import Path

CONTEXT_LINES = 30

index = json.load(open("cache/index.json"))
results = []
skipped = []

for key, entry in index.items():
    if not entry.get("logs_cached"):
        continue

    z = zipfile.ZipFile(entry["logs_path"])
    names = z.namelist()

    for job in entry["failed_jobs"]:
        if job["name"] == "Total Success":
            continue

        safe = job["name"].replace("/", "_")
        match = None
        for n in names:
            if "/" not in n and safe in n:
                match = n
                break
        if match is None:
            skipped.append(job["name"])
            continue

        lines = z.read(match).decode("utf-8", errors="replace").splitlines()
        error_lines = [i for i, line in enumerate(lines) if "##[error]" in line]
        if not error_lines:
            print(f"  no ##[error] in: {job['name']}")
            continue

        last = error_lines[-1]

        # Ginkgo prints a summary at the end; bats prints "not ok" at the
        # moment of failure, which can be thousands of lines earlier. So
        # search the WHOLE log for a real test-failure marker, not just
        # the tail. Fall back to a window before ##[error] if none found.
        MARKERS = ("not ok ", "[FAIL]", "--- FAIL:", "Summarizing")
        hits = [i for i, ln in enumerate(lines) if any(m in ln for m in MARKERS)]

        if hits:
            anchor = hits[-1]
            start = max(0, anchor - 5)
            end = min(len(lines), anchor + 25)
        else:
            start = max(0, last - CONTEXT_LINES)
            end = last + 1

        excerpt = "\n".join(ANSI.sub("", line[29:]) for line in lines[start:end])

        results.append({
            "run_id": entry["run_id"],
            "url": entry["url"],
            "job_name": job["name"],
            "total_lines": len(lines),
            "excerpt_lines": last - start + 1,
            "excerpt": excerpt,
        })

with open("extracted.json", "w") as f:
    json.dump(results, f, indent=2)

total_in = sum(r["total_lines"] for r in results)
total_out = sum(r["excerpt_lines"] for r in results)
total = len(results) + len(skipped)
print(f"\nextracted {len(results)} of {total} failed jobs "
      f"({len(skipped)} had no matching log file in the archive)")
print(f"{total_in} log lines -> {total_out} lines kept "
      f"({100 * (1 - total_out / total_in):.1f}% reduction)")
