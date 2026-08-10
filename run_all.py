#!/usr/bin/env python3
"""Run the full pipeline: fetch -> extract -> rules -> LLM -> report."""
import argparse
import subprocess
import sys

STEPS = [
    ("fetch_flakes.py", "Fetching failed runs and caching logs"),
    ("extract.py", "Extracting failure regions"),
    ("categorize.py", "Applying regex rules"),
    ("llm_categorize_v2.py", "Classifying with local LLM"),
    ("report.py", "Grouping failures across runs"),
]

ap = argparse.ArgumentParser()
ap.add_argument("--limit", type=int, default=20,
                help="how many failed runs to fetch")
ap.add_argument("--skip-fetch", action="store_true",
                help="use the existing cache instead of downloading")
args = ap.parse_args()

for script, desc in STEPS:
    if script == "fetch_flakes.py":
        if args.skip_fetch:
            print(f"--- skipping {script}")
            continue
        cmd = [sys.executable, script, "--limit", str(args.limit)]
    else:
        cmd = [sys.executable, script]

    print(f"\n=== {desc} ===")
    if subprocess.run(cmd).returncode != 0:
        sys.exit(f"failed at {script}")

print("\nDone. See report output above; details in extracted.json")
