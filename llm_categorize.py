import json
import ollama

MODEL = "llama3.1:8b"

CATEGORIES = [
    "network",         # downloads, mirrors, connection drops
    "timing",          # race conditions, timeouts, ordering
    "resource",        # out of memory or disk
    "infrastructure",  # VM/runner died before tests ran
    "real-failure",    # legitimate failure, NOT a flake
    "unknown",         # not confident
]

PROMPT = """You are triaging a failure from Podman's CI.

Below is the relevant excerpt from the job log.

Classify the root cause as exactly one of:
{cats}

Rules:
- "real-failure" means the code or PR is genuinely at fault, not a flake.
- Use "unknown" if the excerpt does not contain enough evidence.
  Do not guess.

Respond with ONLY a JSON object, no other text:
{{"category": "...", "confidence": "high|medium|low", "reason": "one sentence"}}

Job: {job}

Log excerpt:
{excerpt}
"""


def ask(job_name, excerpt):
    resp = ollama.chat(
        model=MODEL,
        messages=[{
            "role": "user",
            "content": PROMPT.format(
                cats="\n".join(f"- {c}" for c in CATEGORIES),
                job=job_name,
                excerpt=excerpt[:4000],
            ),
        }],
        options={"temperature": 0},
    )
    text = resp["message"]["content"].strip()
    text = text.replace("```json", "").replace("```", "").strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"category": "unknown", "confidence": "low",
                "reason": f"could not parse model output: {text[:80]}"}


results = json.load(open("extracted.json"))
todo = [r for r in results if not r.get("rule_category")]
print(f"{len(todo)} failures need the LLM\n")

for i, r in enumerate(todo, 1):
    print(f"[{i}/{len(todo)}] {r['job_name']}")
    verdict = ask(r["job_name"], r["excerpt"])
    r["llm_category"] = verdict.get("category")
    r["llm_confidence"] = verdict.get("confidence")
    r["llm_reason"] = verdict.get("reason")
    print(f"    -> {r['llm_category']} ({r['llm_confidence']}): {r['llm_reason']}\n")

json.dump(results, open("extracted.json", "w"), indent=2)
