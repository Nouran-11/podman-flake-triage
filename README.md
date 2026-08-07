# Podman CI Flake Triage

Automated triage of flaky test failures in Podman's GitHub Actions CI.

Built during MLH Global Hack Week: Agents (Aug 7-13, 2026).

## Status
Work in progress.

## Pipeline
1. Fetch failed workflow runs and cache logs locally
2. Extract the failing region from ~28MB of logs per run
3. Categorize the failure (rules first, local LLM for the rest)
4. Report findings
