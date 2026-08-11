"""Normalise a failure into a stable signature.

Ports, hashes, container IDs, timestamps and durations differ between
runs of the same underlying flake. Stripping them lets identical causes
group together.
"""
import re

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


# Lines that name a specific failing test are far more diagnostic than
# suite-level summaries, which are identical across unrelated failures.
NAMED = ("[FAIL]", "[TIMEDOUT]", "not ok ", "--- FAIL:")

# Generic lines that must never become a signature on their own: they
# appear in every failure of that framework and merge unrelated causes.
GENERIC = ("FAIL! --", "FAIL! - Suite Timeout", "Test Suite Failed",
           "Ginkgo ran", "Summarizing")


def signature(excerpt):
    """The most diagnostic line in the excerpt, with variable parts removed.

    Prefers a line naming the failing test over a suite summary; falls
    back to any error-bearing line only if no named failure is present.
    """
    named, other = None, None
    for line in excerpt.splitlines():
        s = line.strip()
        if len(s) < 15 or any(g in s for g in GENERIC):
            continue
        if any(k in s for k in NAMED):
            if named is None or len(s) > len(named):
                named = s
        elif any(k in s for k in SIGNAL):
            if other is None or len(s) > len(other):
                other = s
    best = named or other
    return normalise(best) if best else None
