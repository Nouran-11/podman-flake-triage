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
