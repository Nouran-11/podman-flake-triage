"""Tests for failure signature extraction.

Fixtures are trimmed from real Podman CI logs.
"""
from signatures import normalise, signature


def test_prefers_named_failure_over_ginkgo_summary():
    """The suite summary appears in EVERY Ginkgo failure, so anchoring on
    it merges unrelated failures into one signature."""
    log = """
Running platform specific cleanup
Summarizing 1 Failure:
  [FAIL] run basic podman commands [It] Podman ops with port forwarding
  D:/a/podman/podman/pkg/machine/e2e/basic_test.go:182
Ran 79 of 88 Specs in 2722.827 seconds
FAIL! -- 78 Passed | 1 Failed | 0 Pending | 9 Skipped
Test Suite Failed
"""
    sig = signature(log)
    assert "port forwarding" in sig
    assert "Passed" not in sig


def test_finds_bats_failure_far_from_end():
    """bats prints `not ok` when the test fails, not at the end of the
    run, so tail-anchored extraction misses it."""
    log = "\n".join(
        ["ok 1 some passing test in 100ms"] * 50
        + ["not ok 327 |500| podman network reload in 2627ms"]
        + ["ok 328 another passing test in 90ms"] * 50
    )
    sig = signature(log)
    assert "network reload" in sig


def test_same_flake_different_ports_gets_one_signature():
    """Port numbers differ between runs of the same underlying flake."""
    a = "Error: rootlessport listen tcp 0.0.0.0:5876: bind: address already in use"
    b = "Error: rootlessport listen tcp 0.0.0.0:5912: bind: address already in use"
    assert signature(a) == signature(b)


def test_timestamps_and_hashes_are_normalised():
    a = ('time="2026-08-06T10:52:49Z" level=fatal msg="failed to download '
         'sha256:abc123def456789012345678901234567890"')
    b = ('time="2026-08-07T12:23:49Z" level=fatal msg="failed to download '
         'sha256:fed987cba654321098765432109876543210"')
    assert signature(a) == signature(b)


def test_different_failures_stay_separate():
    a = "not ok 12 |100| podman network reload in 500ms"
    b = "not ok 12 |100| podman image rm --force bogus in 500ms"
    assert signature(a) != signature(b)


def test_ansi_escape_codes_are_stripped():
    """Windows/PowerShell logs carry colour codes that would otherwise
    make two identical errors look different."""
    plain = "Error: cannot bind tcp port 5453: address already in use"
    coloured = ("\x1b[31;1mError: cannot bind tcp port 5453: "
                "address already in use\x1b[0m")
    assert signature(plain) == signature(coloured)


def test_returns_none_when_no_failure_line():
    log = "\n".join(["ok 1 everything fine in 10ms"] * 20)
    assert signature(log) is None


def test_short_lines_are_ignored():
    assert signature("FAIL\nok\nErr") is None


def test_normalise_is_length_capped():
    assert len(normalise("Error: " + "x" * 500)) <= 110
