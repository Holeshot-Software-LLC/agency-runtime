---
title: "Worklog detail: expose and reduce fixture cost"
status: active
category: worklog
created: 2026-07-27
updated: 2026-07-27
tags: [testing, performance, observability, isolation]
related:
  - docs/roadmap/issue-AR-156-restore-cost-bounded-verification.md
  - docs/roadmap/handoffs/issue-AR-119.md
supersedes: []
superseded_by: null
type: worklog
commit: e3284bf
short: e3284bf
date: 2026-07-27
pr: null
related_issues:
  - docs/roadmap/issue-AR-156-restore-cost-bounded-verification.md
---

# Worklog detail: expose and reduce fixture cost

## Purpose

Remove repeated filesystem work from the warning-strict developer loop and
make the remaining controller tail directly measurable without weakening test
isolation or the release gate.

## Approach

Ordinary tests now share one private immutable offline configuration per pytest
process while receiving unique lazy Store and runtime-control paths derived
from their node IDs. Configuration- and environment-identity suites opt into
the historical per-test configuration contract. The local parallel runner now
publishes bounded monotonic phase and per-shard timings in manifest schema v3.

## Challenges encountered

The fixture optimization initially exposed suites that intentionally remove or
inspect `AGENCY_DB_PATH`; those tests were explicitly marked to retain the old
identity contract. Scratch cleanup remains synchronous because the security
boundary owns one identity for the complete tree rather than independent child
identities.

## Decisions and alternatives

The shared configuration points its unused file-level Store fallback at a
directory, so an unmarked test that removes the unique database override fails
closed instead of silently sharing mutable state. Phase instrumentation was
chosen before further cleanup concurrency because the measured result must
justify any expansion of the cleanup identity model.

## Verification

- Uncontended interleaved 437-test comparison: all six arms passed; median
  `4.215s` to `3.015s` (28.5 percent reduction).
- Independent runner contract: 33 passed.
- Independent configuration/identity package: 735 passed, 1 skipped.
- Broader agent sweeps: more than 2,400 passing executions.
- Targeted Ruff check and format, documentation metadata/policy/worklog checks,
  414-file documentation validation, and `git diff --check`: passed.

## Follow-ups

Use manifest v3 evidence to evaluate the remaining identity-bound scratch tail
and repeated validated Store connections under AR-156. Current-head canonical
release and hosted evidence remain outstanding.
