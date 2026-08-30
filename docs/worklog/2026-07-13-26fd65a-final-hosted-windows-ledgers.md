---
title: "Final hosted Windows and ledger closure"
status: active
category: worklog
created: 2026-07-13
updated: 2026-07-13
tags: [worklog, windows, delegation, sqlite, security, ci, documentation]
related:
  - docs/roadmap/issue-AR-07-public-release-readiness.md
  - docs/roadmap/issue-AR-16-linux-python-delegation-compatibility.md
  - docs/roadmap/issue-AR-17-production-hardening-portability.md
  - docs/roadmap/issue-AR-20-full-history-ledger-ci.md
  - docs/roadmap/issue-AR-21-fully-resume-windows-children.md
  - docs/roadmap/issue-AR-22-concurrent-storage-acl-repair.md
  - docs/decisions/0025-self-contained-linked-documentation.md
  - docs/decisions/0037-layered-pinned-supply-chain-gates.md
  - docs/decisions/0039-fail-before-dacl-mutation-under-restricted-windows-tokens.md
  - docs/decisions/0044-preclose-bounded-windows-child-stdin.md
  - docs/RELEASE_CHECKLIST.md
supersedes: []
superseded_by: null
type: worklog
commit: 26fd65a2e117510b7e190d26b1ec0e6f089ce880
short: 26fd65a
date: 2026-07-13
pr: https://github.com/Holeshot-Software-LLC/agency-runtime/pull/18
related_issues:
  - docs/roadmap/issue-AR-07-public-release-readiness.md
  - docs/roadmap/issue-AR-16-linux-python-delegation-compatibility.md
  - docs/roadmap/issue-AR-17-production-hardening-portability.md
  - docs/roadmap/issue-AR-20-full-history-ledger-ci.md
  - docs/roadmap/issue-AR-21-fully-resume-windows-children.md
  - docs/roadmap/issue-AR-22-concurrent-storage-acl-repair.md
---

# Worklog detail: Close final hosted Windows and ledger gaps

## Purpose

Close the defects exposed by the final hosted matrix without waiving Windows
PowerShell reliability, storage privacy, complete Git-history validation, or
the exact release gates.

## Approach

- Validate the history-derived documentation ledger only after checking out
  the complete durable pull-request head. Keep tests and merge-safety checks on
  GitHub's synthetic merge result.
- Replace scheduling-dependent bounded stdin priming with an anonymous pipe
  filled and closed before Windows child creation. Keep larger input on the
  exact asynchronous writer.
- Require complete native thread enumeration, exactly one primary thread, and
  reopened-handle process ownership before releasing the single runtime-owned
  suspension.
- Serialize SQLite storage ACL inspect, apply, and postcheck operations across
  Store instances. Retry optional sidecars only after fresh metadata proves
  disappearance or identity replacement.

## Challenges encountered

The first hosted rerun proved that waiting for a background writer's completion
event was not a portable EOF boundary even though local native tests passed.
Security review then identified three additional native edges: incomplete
Thread32 enumeration, recycled thread IDs, and suppressed anonymous-pipe close
errors. Each now fails before child execution or cleans up the suspended child.

The full exact-coverage run also exposed one new spawn-failure branch introduced
by the cleanup path. A dedicated regression brought the single fresh invocation
back to exact coverage instead of lowering the gate.

## Decisions and alternatives

- [ADR-0044](../decisions/0044-preclose-bounded-windows-child-stdin.md)
  supersedes the completion-event design in ADR-0043 and records the preclosed
  pipe plus sole-primary-thread ownership contract.
- Repeated ResumeThread calls were rejected because they can drain suspension
  counts owned by another actor.
- Temporary input files were rejected because task content would gain a
  durable filesystem and cleanup lifetime.
- Treating SQLite sidecar ACL errors as universally transient was rejected;
  stable identities and replacement links remain fatal.

## Verification

- Fresh warning-strict non-performance suite: 2,326 passed, 5 skipped, 2
  deselected; exact 100.00% coverage over 17,343 statements and 5,420 branches.
- Native PowerShell companion and multiline stdin boundary regressions: 31
  focused tests passed, including empty, 4096-byte, and 4097-byte input.
- Uninstrumented performance suite: 2 passed.
- Dashboard UI: 60 tests passed at exact line, branch, and function coverage.
- Routing evaluation: all 25 gates passed; p95 8.774 ms, cache p95 0.394 ms,
  150.02 concurrent calls per second, and overlap 8.
- Delegation evaluation: 12 of 12 cases passed.
- Ruff, format, metadata, policy, worklog, tracker, documentation, and
  whitespace checks passed.
- Independent senior code review and security review reported no remaining
  actionable findings after remediation.

## Follow-ups

- Confirm the pushed head on GitHub's Ubuntu Python 3.10 through 3.14, Windows
  Python 3.10 and 3.14, packaging, security, artifact, and CodeQL jobs.
- Merge PR #18, record hosted and merge evidence, reconcile final roadmap
  status, and close every completed tracker item.
