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
