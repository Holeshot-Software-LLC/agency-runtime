---
title: Close Windows ingestion and CI portability gaps
status: active
category: worklog
created: 2026-07-19
updated: 2026-07-19
tags:
  - windows
  - portability
  - security
  - roster
  - ci
related:
  - docs/roadmap/issue-AR-104-run-hosted-portability-gates-in-trusted-boundaries.md
  - docs/roadmap/issue-AR-106-portable-windows-policy-and-posix-simulations.md
  - docs/decisions/0021-full-companion-policy-with-precedence.md
  - docs/decisions/0030-versioned-quantitative-evaluation-gates.md
  - docs/decisions/0037-layered-pinned-supply-chain-gates.md
  - docs/decisions/0066-package-audited-roster-and-sync-quarantined-deltas.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: worklog
commit: 987c32ae6c8aef2766b1779d06ec1a63c64c0491
short: 987c32a
date: 2026-07-19
pr: https://github.com/Holeshot-Software-LLC/agency-runtime/pull/104
related_issues:
  - docs/roadmap/issue-AR-104-run-hosted-portability-gates-in-trusted-boundaries.md
  - docs/roadmap/issue-AR-106-portable-windows-policy-and-posix-simulations.md
---

# Worklog detail: Close Windows ingestion and CI portability gaps

## Purpose

Close the remaining Windows policy-identity, portable simulation, dependency-review, and roster-ingestion mutation gaps that prevented the trusted hosted portability matrix from being an honest release gate.

## Approach

- Bound Windows policy ownership to the caller's binary token SID while retaining exact DACL and mutation-safety checks.
- Reconfigured bootstrap standard streams as UTF-8 before dispatch so Windows console encoding cannot corrupt structured CLI output.
- Kept POSIX simulations process-local by routing platform operations through the injected OS facade and using `fchmod`.
- Replaced directory-mtime assumptions with bounded, deterministic, no-follow directory receipts covering exact entry-name bytes, stable entry fingerprints, and every traversed directory.
- Bracketed snapshots with identity checks and revalidated the complete source receipt once after all file reads, preserving linear work instead of multiplying full-tree verification by file count.
- Reduced the dependency-review fallback to normal runtime requirements plus the pinned audit tool.

## Challenges encountered

Windows account aliases are localized and can differ from the binary token identity used by the operating system. Directory modification time is also insufficient evidence for every add, remove, rename, or replacement mutation. The authoritative branch-coverage run exposed one unvisited no-receipt-collector branch, which was closed with a focused test rather than a production-code exception.

## Decisions and alternatives

The ingestion boundary records one exact, source-wide receipt set and revalidates it after all file reads. Unknown, ambiguous, linked, reparse, special, or over-budget entries continue to fail closed. Known deterministic upstream corruption may be repaired only through registered remediation rules with bounded evidence; the production trust model is unchanged.

## Verification

- Warning-strict full suite: 6,053 passed, 20 skipped, 3 deselected.
- Coverage: 39,348 statements and 13,288 branches at 100.00%, with zero missed lines or branches.
- Performance suite: 3 passed; 6,073 deselected.
- Dashboard UI: 88 Node tests passed.
- Routing and delegation evaluation: all gates passed; routing and delegation recall/decision gates were 1.0.
- Full roster evaluation: 263 approved and enabled; zero quarantined or retired; all participation, recall, and leak gates passed.
- Documentation metadata, policy availability, worklog, release hygiene, Ruff lint/format, Bandit high-severity scan, exact-runtime dependency audit, zizmor offline scan, and `git diff --check` passed.

## Follow-ups

Run the Windows 3.10 and 3.14 hosted matrix plus the dependency-review workflow under [AR-104](../roadmap/issue-AR-104-run-hosted-portability-gates-in-trusted-boundaries.md) and [AR-106](../roadmap/issue-AR-106-portable-windows-policy-and-posix-simulations.md).
