import json
import zipfile
from pathlib import Path

CONTEXT_LINES = 30

index = json.load(open("cache/index.json"))
results = []

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
            print(f"  no log file for job: {job['name']}")
            continue

        lines = z.read(match).decode("utf-8", errors="replace").splitlines()
        error_lines = [i for i, line in enumerate(lines) if "##[error]" in line]
        if not error_lines:
            print(f"  no ##[error] in: {job['name']}")
            continue

        last = error_lines[-1]
        start = max(0, last - CONTEXT_LINES)
        excerpt = "\n".join(line[29:] for line in lines[start:last + 1])

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
print(f"\nextracted {len(results)} failures")
print(f"{total_in} log lines -> {total_out} lines kept "
      f"({100 * (1 - total_out / total_in):.1f}% reduction)")
