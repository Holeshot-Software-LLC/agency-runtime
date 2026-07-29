---
title: "Worklog detail: Reconcile consumed Codex child callback"
status: active
category: worklog
created: 2026-07-29
updated: 2026-07-29
tags: [codex, activation, hooks, callback, evidence]
related:
  - docs/roadmap/issue-AR-199-restore-codex-workforce-evidence.md
  - docs/roadmap/handoffs/issue-AR-199.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: worklog
commit: ef41cff
short: ef41cff
date: 2026-07-29
pr: null
related_issues:
  - docs/roadmap/issue-AR-199-restore-codex-workforce-evidence.md
---

# Worklog detail: Reconcile consumed Codex child callback

## Purpose

Preserve the real SubagentStart child lineage when Codex projects a different
PostToolUse callback identity for the completed spawn.

## Approach

The PostToolUse bridge validates Codex's bounded rooted response and reconciles
only one already-consumed native-hook activation for the exact planned task
label, selected specialist version and prompt hash, and real
`codex-agent:<UUID>` lineage. Unconsumed, ambiguous, mismatched, or synthetic
lineage remains in the fail-closed path.

## Evidence

Source-live trace `019faeaf-3917-7673-b9e7-cd149b7ac0ca` contained one real
activation consumption and specialist load, but the delegation retained
`task:unit_05d45f7553` and Stop correctly returned `continue`. The focused
regression reproduces the different callback identity after SubagentStart
consumption and requires the delegation to bind the real child and grant.

Subsequent trace `019faeca-406f-7d20-b2e7-6b1741b5a8af` showed that accepting
a different nonempty identity was insufficient. Commit `e41df93` records the
correct missing-identity boundary without weakening consumed-grant validation.

## Verification

- All 17 tests in `tests/test_codex_activation_canary.py` passed.
- Ruff check and format passed for the changed source and test.
- Documentation validation passed for 518 Markdown files.

## Follow-ups

Refresh the Codex launcher from this checkpoint, prove the isolated canary,
then run the named fast spine before PR and exact-install verification.
