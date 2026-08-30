---
title: "Worklog detail: Add secure parallel change loop"
status: active
category: worklog
created: 2026-07-26
updated: 2026-07-26
tags: [testing, performance, security, process-containment, developer-experience]
related:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-156-restore-cost-bounded-verification.md
  - docs/decisions/0030-versioned-quantitative-evaluation-gates.md
  - docs/decisions/0091-least-privilege-subprocess-environments.md
supersedes: []
superseded_by: null
type: worklog
commit: c5d5631
short: c5d5631
date: 2026-07-26
pr: null
related_issues:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-156-restore-cost-bounded-verification.md
---

# Worklog detail: Add secure parallel change loop

## Purpose

Provide a supported local change loop for the 34-to-43-minute warning-strict
Python corpus without weakening the separate serial, coverage, performance, or
compatibility release gates.

## Approach

The runner reuses the governed four-way file partition and one stable,
contract-attested private Python runtime. Each shard receives an isolated HOME,
TEMP, and pytest base directory plus a least-privilege environment and an
explicit dependency bridge. The owned-process facade now supports public
cross-thread cancellation and optional bounded head-and-tail output, allowing a
failed or interrupted shard to cancel and reap the complete descendant tree.

One repository-global private byte lock serializes real runs. Scratch state is
recreated under that lock and removed afterward. Fixed latest logs are cleared
as a set, atomically replaced, and bound to one run ID and manifest. Immutable
ownership receipts distinguish Agency state from unknown collisions; mutable
runtime-contract changes rebuild only an attested Agency-owned root. Dry-run
projects the same plan without creating any filesystem resource.

## Challenges encountered

The first design grew to 1,421 orchestration lines and retained unique run
directories. It was rejected as new maintenance and disk-retention debt. The
smaller fixed-root design then exposed four independent review blockers:
mutable runtime identities could poison reuse, interrupted log sets could mix
generations, receipt publication could leave a permanent partial file, and the
initial dry-run still created a venv and Node mirror. The final design separates
runtime, storage, and orchestration policy and has mutation-resistant recovery
tests for each case.

## Decisions and alternatives

Four duplicated per-shard environments were rejected in favor of one read-only
attested runtime with per-shard state roots. Inheriting the caller environment
was rejected because local test code could receive unrelated credentials.
Retaining unbounded unique run directories was rejected in favor of one
bounded latest log set. The runner remains a developer feedback loop; ADR-0030's
canonical serial and quantitative release gates remain unchanged.

## Verification

- Author-focused package: 212 passed, 15 skipped.
- Independent focused package: 211 passed, 15 skipped in 24.86 seconds.
- Independent real private-venv and root-exited descendant smoke: 2 passed.
- Live cancellation facade returned exit 130, classified cancellation, and
  reaped the descendant with no worker error.
- Fresh-home direct and module dry-runs were byte-identical, covered 274 files,
  and left runtime, requested-home, and global-lock snapshots unchanged.
- Focused Ruff, format, byte-compilation, documentation, and diff checks passed.

## Follow-ups

AR-156 still requires three uncontaminated warm full-corpus runs showing at
least 30 percent median wall-clock improvement. Current-head serial, coverage,
performance, artifact, and installed smoke gates remain separate release work.
