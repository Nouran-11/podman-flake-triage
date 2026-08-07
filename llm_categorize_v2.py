import json
import ollama

MODEL = "llama3.1:8b"

PROMPT = """Triage one failed job from Podman's CI.

STEP 1. Quote the single line from the log that shows WHY the job failed.
Copy it exactly. If no line shows a cause, write NONE.

STEP 2. Using only that line, choose one category:

network
  Downloading something from outside the runner failed.
  Signals: "Failed to fetch", "unexpected EOF" while downloading,
  apt/mirror errors, connection reset, a URL in the error.

timing
  A test failed or timed out because of ordering, waiting, or a race.
  Signals: [TIMEDOUT], "Suite Timeout Elapsed", expected output was
  empty, a socket/connection inside the test did not become ready,
  a service failed to start, a resource was not there yet.
  NOTE: most flaky test failures are this. If exactly one spec out of
  many failed and the cause is not a download, prefer timing.

infrastructure
  The tooling/environment broke before or around the tests.
  Signals: dependency resolution failed, package build failed,
  the runner or VM died.

real-failure
  The PR itself is wrong. NOT a flake.
  Signals: lint/format violation, docs out of sync with --help,
  a policy check like "PR does not include tests".

unknown
  The excerpt names a failing test but shows no cause.
  Choosing unknown is CORRECT when evidence is missing. Do not guess.

Do NOT use "resource" - it is not a category here.

Job: {job}

Log:
{excerpt}

Answer with ONLY this JSON:
{{"evidence": "the exact line or NONE", "category": "...", "reason": "one sentence"}}
"""


def ask(job, excerpt):
    r = ollama.chat(
        model=MODEL,
        messages=[{"role": "user",
                   "content": PROMPT.format(job=job, excerpt=excerpt[:8000])}],
        options={"temperature": 0},
    )
    t = r["message"]["content"].strip().replace("```json", "").replace("```", "").strip()
    try:
        return json.loads(t)
    except json.JSONDecodeError:
        return {"category": "unknown", "evidence": "", "reason": f"unparseable: {t[:60]}"}


rs = json.load(open("extracted.json"))
for i, r in enumerate(rs):
    v = ask(r["job_name"], r["excerpt"])
    r["llm_v2_category"] = v.get("category")
    r["llm_v2_evidence"] = v.get("evidence")
    r["llm_v2_reason"] = v.get("reason")
    print(f"[{i}] {r['llm_v2_category']:<16} {r['job_name'][:30]}")
    print(f"     evidence: {str(v.get('evidence'))[:90]}")

json.dump(rs, open("extracted.json", "w"), indent=2)
