# Hand labels by Nouran, Aug 8 2026, from full excerpts.
# Confidence noted where the call is a judgement rather than explicit.

LABELS = {
    0:  "timing",        # [TIMEDOUT] curl connect to machine socket; suite hit 50m wall
    1:  "timing",        # not ok 174 podman import (ci:parallel) - same test as #11
    2:  "real-failure",  # gofumpt: libpod/runtime_ctr.go not formatted
    3:  "real-failure",  # --authfile in --help but not in podman-build.1.md
    4:  "timing",        # [TIMEDOUT] list machine while starting; 50m wall
    5:  "network",       # apt: archive.ubuntu.com fetch failed, mirror sync
    6:  "unknown",       # 1 of 2196 specs; no cause visible in excerpt
    7:  "network",       # apt: same mirror-sync failure
    8:  "real-failure",  # PR genuinely has no tests
    9:  "infrastructure",# pip ResolutionImpossible in pre-commit env
    10: "timing",        # [TIMEDOUT] proxy settings over ssh; 50m wall
    11: "timing",        # podman import: "mkdir /bin: no such file" (ci:parallel race)
    12: "unknown",       # [FAIL] podman cp, 2 failed; cause not in excerpt
    13: "timing",        # port forwarding + gvproxy
    14: "network",       # qcow2.zst download: unexpected EOF
    15: "timing",        # machine reset with other machines idle
    16: "timing",        # exec output empty, expected volcontent (race)
    17: "timing",        # identical failure, rootless
    19: "network",       # qcow2.zst download: unexpected EOF
    18: "timing",        # quadlet image tag: systemctl_start failed
}
