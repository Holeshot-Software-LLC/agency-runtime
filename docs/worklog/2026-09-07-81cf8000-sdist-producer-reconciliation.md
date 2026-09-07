---
title: "Reconcile AR-184 with detached Linux producer proof"
status: active
category: worklog
created: 2026-09-07
updated: 2026-09-07
tags: [backlog, packaging, linux]
related:
  - docs/roadmap/issue-AR-184-normalize-private-posix-sdist-modes.md
  - docs/roadmap/acceptance/evidence/AR-183-AR-184-private-linux-producer-20260907.md
supersedes: []
superseded_by: null
type: worklog
commit: 81cf80001d955f251b1ce2449a39cd2ed6b33081
short: 81cf8000
date: 2026-09-07
pr: null
related_issues:
  - docs/roadmap/issue-AR-184-normalize-private-posix-sdist-modes.md
---

# Worklog detail: Reconcile AR-184 with detached Linux producer proof

## Purpose

Remove the stale implication that the current Linux sdist producer remains
broken, while preserving the real Windows comparison requirement.

## Approach

Reuse AR183's exact08fab1c4 detached umask077 producer and498focused tests.
Record its canonical sdist census and existing exact-mode/convergence guards.
Update the sequential backlog table with all already-published dispositions.

## Challenges encountered

Two old records duplicate the same Linux producer observation. One immutable
receipt supplies both; rebuilding only to repeat it would add no evidence.
The original Windows/merged-set requirement remains materially distinct.

## Decisions and alternatives

No source or policy change, no acceptance verdict or silent checkbox rewrite.
Keep historical failed raw-mode census clearly historical; retain cross-platform
proof for the owner rather than calling Linux output a Windows pass.

## Verification

Shared builder/Twine/portable verifier and focused results are reused explicitly.
Metadata, policy, ledger, docs, strict tracker, Ruff and diff publication checks.
No provider call, owner install or exhaustive gate.

## Follow-ups

AR184 remains in_progress. Publish then AR185; future Windows comparison must
use exactly08fab1c4 or rebuild both platforms from one newly frozen SHA.

Substantive `81cf8000` records the shared real Linux producer against AR184 while preserving original acceptance states and exact cross-platform hold.
