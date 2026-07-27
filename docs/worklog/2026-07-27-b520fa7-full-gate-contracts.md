---
title: "Align hardened full-gate contracts"
status: active
category: worklog
created: 2026-07-27
updated: 2026-07-27
tags: [testing, security, isolation, traceability, performance]
related:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-176-align-full-gate-contract-fixtures.md
supersedes: []
superseded_by: null
type: worklog
commit: b520fa765ffdef93ad499a088f79d247ce910e75
short: b520fa7
date: 2026-07-27
pr: null
related_issues:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-176-align-full-gate-contract-fixtures.md
---

# Worklog detail: Align hardened full-gate contracts

## Purpose

Restore the exact warning-strict release corpus after it exposed eleven
integration-test failures that focused security and dashboard packages had not
collected together.

## Approach

Preserved production configuration, executable-currentness, and append-only
authority contracts. Marked two file-identity tests so the global synthetic
database override cannot replace their explicit configuration. Updated process
doubles to accept the current security arguments, materialized a strict path
fixture, and made authority/cursor fixtures model current immutable rows and
SQLite behavior. Corrected the missing-Node smoke diagnostic while leaving
process freezing and revalidation unchanged.

## Challenges encountered

The first full corpus spent 33 minutes before reporting the eleven failures and
retained roughly 13 GB in its monolithic process. Ten failures were stale tests;
one was a genuine Low diagnostic defect. Treating them as one production
regression or immediately repeating the full run would have obscured both the
root causes and the cost signal.

## Decisions and alternatives

Production keyword arguments, strict path resolution, active-basis checks, and
immutable event identifiers were not relaxed for test compatibility. The
original failed result remains part of the evidence. The rerun is admitted only
after all eleven node IDs and one combined neighboring package pass.

## Verification

- Original exact corpus: 8,010 passed, 61 skipped, 1 expected failure, 11
  failed in 33:25.
- Original eleven node IDs after repair: 11 passed in 1.53 seconds.
- Twelve touched and neighboring files: 670 passed, 1 platform skip in 2:42.
- Focused Ruff lint/format, documentation validation across 437 files, and
  `git diff --check` passed.

## Follow-ups

- [AR-176](../roadmap/issue-AR-176-align-full-gate-contract-fixtures.md): rerun
  the exact full corpus and retain its exact result.
- [AR-156](../roadmap/issue-AR-156-restore-cost-bounded-verification.md): keep
  the isolated sharded loop as the normal feedback path and reserve this
  monolithic session for final release evidence.
