# Findings from Podman CI logs

## Scale
- ~28 MB of logs per failed run
- 56 jobs per run, only 3-4 fail

## Job naming
Job names encode four axes:
test-type (int/sys/unit/bud/apiv2/...), local vs remote,
root vs rootless, OS (fedora-current/prior/rawhide, debian-sid, windows, macos).
Maintainers use these same axes when writing flake reports.

## Finding the failure
- `##[error]` is the universal marker across all job types
- BUT there can be several per job, and some steps are allowed to fail
  (e.g. `wsl --uninstall` failing is harmless, job continues)
- Use the API's `failed_steps` to identify which error actually matters
- `Total Success` is a gate job with no real error - filter it out

## Test frameworks produce different markers
- bats (sys tests): `not ok`
- Ginkgo (e2e): `[FAIL]` plus test name and file:line
- Go test: `--- FAIL:`
- Some jobs fail with NO test marker at all (infra died before tests ran)

## Log size varies hugely
387 lines for an infra failure, 4822 for a test failure.
A fixed-size extraction window will be wrong for one of them.

## Categories seen so far
- Network: VM image download failed with "unexpected EOF" (Oracle object storage)
- Test failure: port forwarding / gvproxy test, 1 of 79 specs failed

## Rule-based classification results (16 failures, Aug 5-7)

4/16 (25%) classified by regex alone, no LLM needed:
- network/apt-mirror: archive.ubuntu.com fetch failed, exit code 100
- network/vm-image-download: qcow2.zst download "unexpected EOF"

The qcow2 download flake hit fedora-prior (Aug 6) AND debian-sid (Aug 7).
Same root cause, different distro, different day = recurring infra flake.

## PROBLEM: fixed 30-line window is often teardown noise

6 of the 12 unmatched failures are lima jobs whose last 30 lines are
all identical VM cleanup:
  Removing serial.sock / serialv.sock / ssh.sock / Deleted "podman-ci"
  ##[error]Process completed with exit code 2

The actual failure (Ginkgo "Summarizing 1 Failure") sits ABOVE that
teardown block. A fixed window before ##[error] can miss it entirely
when cleanup is verbose.

Fix to try: instead of a blind 30-line window, search backwards from
##[error] for a framework marker ("Summarizing", "[FAIL]", "not ok",
"--- FAIL:") and anchor the excerpt there. Fall back to the fixed
window only if no marker is found.

## NOT every CI failure is a flake

"Validate source code changes" produced two failures of different kinds:
- Makefile:775 tests-included Error 1 -> PR genuinely lacks tests.
  A real, correct failure. Must NOT be reported as a flake.
- Makefile:284 lint Error 3 -> pre-commit pip build deps failed
  (dependency resolution). That IS an infra flake.

So the categoriser needs a "legitimate failure / not a flake" outcome,
not just flake categories.

## Exit codes carry signal
- 100 -> apt / package fetch
- 1   -> windows winmake.ps1 wrapper around ginkgo
- 2   -> make-wrapped test failure

## Recurring: windows machine e2e
4 of 16 failures are windows machine (hyperv x3, wsl x1), all ending
at winmake.ps1:102 running ginkgo.exe. Strongest recurring candidate
in this sample.

## Single-spec failures = flake signal
- macos applehv: 78 Passed | 1 Failed | 5 Skipped
- int remote rootless: 2195 Passed | 1 Failed | 335 Skipped
One failure out of thousands is very unlikely to be a real regression.

## KEY INSIGHT: frameworks differ in WHERE the failure appears

Not just in marker syntax, but in position:
- Ginkgo prints a "Summarizing 1 Failure" block at the END of the run
- bats prints "not ok <n>" AT THE MOMENT the test fails, which can be
  thousands of lines before the end of the log
- Go test prints "--- FAIL:" inline too

Consequence: any extraction anchored on the TAIL of the log silently
misses bats failures entirely. Searching backwards ~400 lines from
##[error] is not enough. The whole log has to be scanned for markers.

## Failed attempt worth recording

First fix searched backwards 400 lines for markers including
"Error 1/2/3". That matched the trailing make line
  make: *** [Makefile:749: localapiv2-bash] Error 3
which sits at the very end of every failed make-wrapped job. Anchoring
5 lines above it landed in PASSING output ("ok 2220", "ok 2221").

Lesson: make/shell exit lines are not test-failure markers. They tell
you a command failed, not which test failed. Marker list must be
restricted to genuine test-framework output:
  "not ok ", "[FAIL]", "--- FAIL:", "Summarizing"

## Sample sizes so far
- 15 runs cached (5 permanently failed to download)
- 20 failures extracted
- 190,924 log lines -> ~378 kept (99.8%)
- 4/20 (20%) classified by regex, no LLM

## Recurring flake candidates in this sample
- windows machine hyperv: 4 of 20 failures
- windows machine wsl: 1 more (5/20 = windows machine e2e family)
- qcow2.zst download EOF: fedora-prior + debian-sid, 2 different days

## Meta note
Downloading the log archives repeatedly failed with
ChunkedEncodingError - the same class of transient network failure
this tool is built to categorise. Retry-and-skip logic was added for
exactly the reason the tool exists.

## RESULT: llama3.1:8b scores 15% (3/20) against hand labels

Hand labels (n=20): timing 10, network 4, real-failure 3,
infrastructure 1, unknown 2.

LLM output: resource 10, real-failure 10. Nothing else. It never
emitted timing, network, infrastructure or unknown, despite all four
occurring in the data. Mode collapse onto two labels, not classification.

Baselines it loses to:
- always answer "timing": 10/20 = 50%
- random over 6 classes: ~17%
- regex rules: 4/4 correct on network cases, where the LLM got 0/4

Never returned "unknown"; reported "high" confidence on all 20,
including two cases where the excerpt genuinely lacks the cause.
Self-reported confidence is unusable here.

To test one at a time:
1. Categories are bare words with no definitions or exclusions
2. Prompt asks for the label first, so the reason justifies a
   pre-chosen answer
3. Nothing makes declining acceptable, so "unknown" is never used
4. 4000-char truncation may cut the marker in longer excerpts

## Prompt v2: 80% (16/20), up from 15%

Same model (llama3.1:8b), same 20 failures. Four changes:
1. Categories defined with signals and exclusions, not bare words
2. Model must quote the evidence line BEFORE choosing a label
3. "unknown" declared explicitly correct when evidence is missing
4. Truncation 4000 -> 8000 chars

Effect: mode collapse gone. All six... four used categories appear.
Every answer quotes a real line from the log - no fabricated causes.

The 4 disagreements are all boundary cases, not errors:
- #6, #12: I said unknown, model said timing. Its guess is defensible.
- #11, #18: I said timing, model said infrastructure. Genuinely ambiguous
  (mkdir /bin during unpack; systemctl_start failed).

Still unfixed: model returned "unknown" 0/20 despite the prompt saying
it is correct to do so. Small models appear reluctant to decline even
when instructed. Banning "resource" worked; encouraging "unknown" did not.

## Scaled to 57 runs / 102 failures

- 102/102 excerpts still contain a real failure marker
- 1,423,501 log lines -> 3,090 (99.8% reduction)
- Regex rules: 6/102 (6%), down from 20% on the n=20 sample.
  Two hardcoded patterns do not generalise; the LLM does the real work
  at scale. Rules stay valuable because they are exact and free where
  they apply, not because they cover much.
- 14 failed jobs had no matching log file in the archive (~12%).
  Cause not yet identified - either GitHub omits some job logs or the
  name matching has a gap. Currently skipped silently; should at least
  be counted and reported.
- Accuracy remains measured on the original hand-labelled n=20 only.

## Cross-run report findings (102 failures, 57 runs)

Job frequency: windows machine hyperv 15, macos machine applehv 11,
Validate source code changes 11. Top 3 = 36% of all failures.

ALL 8 suite timeouts are windows machine hyperv. Zero on macos or wsl.
This is a suite-budget problem specific to one job, not a flaky test -
the fix is a bigger --timeout or fewer specs, not a test rewrite.

Likely REAL regression, not a flake:
  [FAIL] Podman build [It] podman remote build uses the server seccomp
  default (#24318)
Failed on 5 platforms in the same window: debian-sid, fedora-current,
fedora-prior, fedora-rawhide, rootless fedora-current. A flake does not
hit five OSes at once. Test name references an existing issue.

Cross-platform machine failures (applehv AND hyperv):
  - machine init --now with --update-connection
  - set machine cpus, disk, memory
Shared machine code, not platform-specific.

This is the value of grouping: none of these are visible when triaging
one failure at a time.

## Signature clustering: 102 failures -> 47 signatures

Normalising ports, hashes, timestamps and test IDs out of the error line
reveals clusters invisible to test-name grouping.

Largest clusters:
- rootless pasta networking: 12 failures across 3 signatures
  (connect/disconnect w/ port forwarding, same + pasta forwarder,
  network reload - pasta forwarder), plus 4x "netavark: no static ips
  provided" on the same four jobs. ~16 failures, likely one cause.
- lima hostagent "ha.pid did not start up": 6x across FOUR different
  jobs (apiv2, compose_v2, unit, upgrade). Looks like four problems in
  a per-job view; is one VM startup failure.
- windows machine hyperv suite timeout: 6x, single job.
- quadlet nested_server_name assertion: 5x across 5 jobs.
- seccomp #24318: 5x across 5 jobs.

## Classifier self-consistency problem (found via clustering)

The same normalised signature receives different categories on different
occurrences:
  hostagent ha.pid        -> infrastructure AND timing
  seccomp #24318          -> real-failure AND timing
  network reload pasta    -> real-failure AND timing
  set machine cpus/disk   -> infrastructure AND real-failure

Identical evidence, different verdict. Clusters act as their own ground
truth here - no extra hand-labelling needed to detect the inconsistency.

Fix: classify once per signature rather than per occurrence. Gives
consistency by construction and cuts LLM calls by ~55% (47 vs 102).

## ANSI stripping recovered 10% of the dataset

Windows/PowerShell logs carry colour escape codes that made lines
unquotable. Stripping them at extraction dropped empty-evidence results
from 11 to 1, and all five categories are now in use (was 4).
Preprocessing fix, not a model or prompt change.
