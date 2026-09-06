---
title: "Retain current proof for implemented Store trust"
status: active
category: worklog
created: 2026-09-05
updated: 2026-09-05
tags: [backlog, security, filesystem, evidence]
related:
  - docs/roadmap/issue-AR-130-revalidate-store-trust.md
  - docs/roadmap/issue-AR-176-align-full-gate-contract-fixtures.md
  - docs/roadmap/AR-404-oldest-first-reconciliation-20260905.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: worklog
commit: 513dd6f4ae0ea122dacd384d1382237e0f8f8a6a
short: 513dd6f4
date: 2026-09-05
pr: null
related_issues:
  - docs/roadmap/issue-AR-130-revalidate-store-trust.md
  - docs/roadmap/issue-AR-176-align-full-gate-contract-fixtures.md
---

# Worklog: retain current Store trust proof

## Purpose

The seventh oldest-first disposition separates the existing trust-cache repair
from missing current performance/platform evidence, without rewriting security.

## Approach

Trace every Store connection through authoritative path/file validation and
stable identity checks. Preserve all four original acceptance criteria. Reserve
native Windows evidence for the owner and hook-budget evidence for the existing
performance owners. Record the prior AR-129 merge in PR #695 at d38e9d13.

## Challenges encountered

The wider non-Windows parent/file package passes 40, fails two, and deselects
39 Windows-named cases (0.84s). Both failures are stale fixtures: one mocks
the pre-extraction OS boundary so the real default-ACL helper probes a missing
synthetic directory and fails closed on ENOENT; the other rejects 0644 against
the explicit owner-only-writable contract inside a private Store namespace.
An in-memory diagnostic with the intended absent-ACL double at the actual
helper boundary passes the existing permission-chain test. It neither edits
tests nor turns the unmodified wider run green. AR-176 owns both repairs.

## Decisions and alternatives

No new policy or relaxed boundary. ADR-0092 prohibits positive trust caching;
batching is the safe optimization. Historical 539.410/408.184ms measurements
remain dated, not a new installed-build performance claim. Retain the issue
instead of fabricating Windows/latency proof or creating a legacy tracker.

## Verification

At d38e9d13, the exact stable-identity, same-inode/same-mtime permission,
existing-connection authority regressions and complete file-trust module pass
19 tests (0.23s). Metadata and strict docs pass for 1123 files before this
detail; policy/worklog/strict tracker/diff checks pass. No runtime/test/script/
workflow changes; reuse this turn's unchanged named spine and UI receipts.
No live inference, new installation, Windows run or exhaustive dispatch.

## Follow-ups

Merge this disposition, then review AR-131. AR-130 remains open for native
Windows and current installed hook-budget proof, plus isolated acceptance.
