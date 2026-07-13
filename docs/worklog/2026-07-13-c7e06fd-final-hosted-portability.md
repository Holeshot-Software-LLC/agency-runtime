---
title: "Final hosted portability fixes"
status: active
category: worklog
created: 2026-07-13
updated: 2026-07-13
tags: [worklog, ci, windows, linux, security, portability, delegation]
related:
  - docs/roadmap/issue-AR-07-public-release-readiness.md
  - docs/roadmap/issue-AR-09-windows-test-isolation.md
  - docs/roadmap/issue-AR-16-linux-python-delegation-compatibility.md
  - docs/roadmap/issue-AR-17-production-hardening-portability.md
  - docs/roadmap/issue-AR-18-work-unit-paths-with-spaces.md
  - docs/decisions/0037-layered-pinned-supply-chain-gates.md
  - docs/RELEASE_CHECKLIST.md
  - docs/THREAT_MODEL.md
supersedes: []
superseded_by: null
type: worklog
commit: c7e06fd61c706e719d432fedfe4d86eb7b9fbd6c
short: c7e06fd
date: 2026-07-13
pr: https://github.com/Holeshot-Software-LLC/agency-runtime/pull/18
related_issues:
  - docs/roadmap/issue-AR-07-public-release-readiness.md
  - docs/roadmap/issue-AR-09-windows-test-isolation.md
  - docs/roadmap/issue-AR-16-linux-python-delegation-compatibility.md
  - docs/roadmap/issue-AR-17-production-hardening-portability.md
  - docs/roadmap/issue-AR-18-work-unit-paths-with-spaces.md
---

# Worklog detail: Close final hosted portability gaps

## Purpose

Close the remaining defects exposed by the GitHub-hosted Linux, Windows, and
Python-version matrix without weakening the repository's security, coverage,
or traceability gates.

## Approach

- Decode roster file URLs before rejecting UNC-shaped paths so Python 3.14 and
  earlier versions apply the same repository-boundary rule.
- Give every delegated subprocess a real stdin pipe and close it explicitly
  when no input is supplied, allowing PowerShell and other EOF-driven hosts to
  finish consistently on Windows and Linux.
- Harden SQLite permission repair against file replacement and optional
  sidecar races with stable identity checks, one bounded sidecar retry, and
  fail-closed database and parent-directory handling.
- Replace process-global operating-system mutation in Linux coverage tests
  with module-local seams, preserving pytest and traceback integrity.
- Probe GitHub's code-scanning capability before registering CodeQL actions.
  Unsupported private repositories emit machine-readable capability evidence
  and still enforce pinned Bandit, Zizmor, and exact dependency-audit gates;
  ambiguous capability failures stop the workflow.
- Recover the longest existing work-unit path containing spaces within strict
  input, match, and suffix budgets so file-overlap delegation and Git-root
  selection do not accept compact decoys.

## Challenges encountered

Hosted runners exposed behavior that the local happy path did not: Python 3.14
changed file-URL conversion details, PowerShell waits for an actual stdin EOF,
SQLite sidecars can appear or disappear while ACLs are repaired, and an
unlicensed private repository rejects CodeQL before analysis is registered.
The final Windows coverage run also had to execute under the real user token
because owner-only ACL tests intentionally exclude the managed sandbox token.

## Decisions and alternatives

- **Treat every CodeQL 403 as unsupported.** Rejected; only the documented
  missing-Code-Security entitlement response is eligible for the compensating
  gate. Permission, rate-limit, malformed, and unknown responses fail closed.
- **Retry every storage target indefinitely.** Rejected; only an optional
  SQLite sidecar receives one retry, while primary database and parent changes
  fail immediately.
- **Split work-unit text on whitespace only.** Rejected because valid absolute
  paths may contain spaces. Recovery is existence-aware and bounded instead.
- **Mutate `os.name` to simulate Linux.** Rejected because the shared mutation
  corrupts unrelated framework behavior and failure reporting.

## Verification

- `pytest` non-performance suite: 2,289 passed, 5 skipped, 2 deselected, with
  100.00% line and branch coverage over 17,215 statements and 5,384 branches.
- Performance suite: 2 passed; routing evaluation passed all 25 gates with
  11.260 ms p95 latency and 125.12 concurrent calls per second.
- Delegation evaluation: 12 of 12 cases passed.
- Dashboard UI: 60 of 60 Node tests passed.
- Ruff lint and format checks, documentation metadata/link/tracker checks,
  release hygiene, and `git diff --check` passed.

## Follow-ups

- Confirm the pushed commit on GitHub's Ubuntu, Windows, packaging, security,
  and capability-aware CodeQL workflows.
- Record hosted evidence and close AR-07, AR-16, AR-17, and AR-18 only after
  PR #18 is merged.
