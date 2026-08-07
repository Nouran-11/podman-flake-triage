#!/usr/bin/env python3
"""Stage 1: fetch failed Podman CI runs and cache their logs locally."""

import argparse
import json
import os
import sys
import time
from pathlib import Path

import requests

# The org was renamed. The API does NOT follow the redirect from the old
# path -- it returns 301 with an empty body, which looks like "no data"
# rather than an error. Always use the new name.
OWNER = "podman-container-tools"
REPO = "podman"

WORKFLOWS = {
    "ci": 286819994,
    "unit-tests": 279899278,
    "validate": 279155368,
    "lima": 287057740,
    "machine-os-pr": 152276636,
}

API = "https://api.github.com"
CACHE = Path("cache")
LOGS = CACHE / "logs"
INDEX = CACHE / "index.json"


def session():
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        sys.exit("Set GITHUB_TOKEN first.")
    s = requests.Session()
    s.headers.update({
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    })
    return s


def check_budget(resp):
    remaining = resp.headers.get("X-RateLimit-Remaining")
    if remaining is None:
        return
    if int(remaining) < 50:
        reset = int(resp.headers.get("X-RateLimit-Reset", 0))
        wait = max(0, reset - int(time.time())) + 5
        print(f"  rate limit low, sleeping {wait}s")
        time.sleep(wait)


def load_index():
    if INDEX.exists():
        return json.loads(INDEX.read_text())
    return {}


def save_index(index):
    CACHE.mkdir(exist_ok=True)
    INDEX.write_text(json.dumps(index, indent=2, sort_keys=True))


def failed_runs(s, workflow_id, limit):
    out, page = [], 1
    while len(out) < limit:
        r = s.get(
            f"{API}/repos/{OWNER}/{REPO}/actions/workflows/{workflow_id}/runs",
            params={"status": "failure", "per_page": 100, "page": page},
        )
        r.raise_for_status()
        check_budget(r)
        batch = r.json().get("workflow_runs", [])
        if not batch:
            break
        out.extend(batch)
        page += 1
    return out[:limit]


def failed_jobs(s, run_id):
    """Which jobs failed, and at which step. The step name alone separates
    infrastructure failures from real test failures, before any parsing."""
    r = s.get(f"{API}/repos/{OWNER}/{REPO}/actions/runs/{run_id}/jobs",
              params={"per_page": 100})
    r.raise_for_status()
    check_budget(r)

    jobs = []
    for job in r.json().get("jobs", []):
        if job.get("conclusion") != "failure":
            continue
        jobs.append({
            "job_id": job["id"],
            "name": job["name"],
            "failed_steps": [
                st["name"] for st in job.get("steps", [])
                if st.get("conclusion") == "failure"
            ],
        })
    return jobs


def fetch_logs(s, run_id, attempt):
    """One archive per run beats one request per job on the rate budget."""
    dest = LOGS / f"{run_id}_{attempt}.zip"
    if dest.exists():
        return dest, False

    r = s.get(f"{API}/repos/{OWNER}/{REPO}/actions/runs/{run_id}/logs",
              allow_redirects=False)
    if r.status_code == 410:
        return None, False   # GitHub expires old logs
    check_budget(r)

    # GitHub redirects to a storage host that rejects our auth header,
    # so follow the redirect ourselves, without credentials.
    if r.status_code in (301, 302, 307):
        src = requests.get(r.headers["Location"], stream=True, timeout=120)
    else:
        r.raise_for_status()
        src = r
    src.raise_for_status()

    # Stream to disk in 1 MB pieces; these archives are large.
    LOGS.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(".part")
    with open(tmp, "wb") as fh:
        for chunk in src.iter_content(chunk_size=1 << 20):
            fh.write(chunk)
    tmp.rename(dest)
    return dest, True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workflow", default="ci", choices=sorted(WORKFLOWS))
    ap.add_argument("--limit", type=int, default=50)
    args = ap.parse_args()

    s = session()
    index = load_index()

    runs = failed_runs(s, WORKFLOWS[args.workflow], args.limit)
    print(f"{len(runs)} failed runs of '{args.workflow}'")

    for i, run in enumerate(runs, 1):
        key = f"{run['id']}_{run['run_attempt']}"
        if key in index and index[key].get("logs_cached"):
            continue

        jobs = failed_jobs(s, run["id"])
        path, downloaded = fetch_logs(s, run["id"], run["run_attempt"])

        index[key] = {
            "run_id": run["id"],
            "attempt": run["run_attempt"],
            "workflow": args.workflow,
            "created_at": run["created_at"],
            "branch": run["head_branch"],
            "sha": run["head_sha"],
            "url": run["html_url"],
            "failed_jobs": jobs,
            "logs_cached": path is not None,
            "logs_path": str(path) if path else None,
        }

        state = "cached" if downloaded else ("expired" if not path else "hit")
        print(f"  [{i}/{len(runs)}] run {run['id']} "
              f"{len(jobs)} failed jobs, logs {state}")

    save_index(index)
    print(f"\n{len(index)} runs in cache -> {INDEX}")


if __name__ == "__main__":
    main()
