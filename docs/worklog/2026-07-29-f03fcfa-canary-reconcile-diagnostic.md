---
title: "Worklog detail: Expose Codex canary reconcile rejection"
status: active
category: worklog
created: 2026-07-29
updated: 2026-07-29
tags: [codex, activation, canary, diagnostics, evidence]
related:
  - docs/roadmap/issue-AR-199-restore-codex-workforce-evidence.md
  - docs/roadmap/handoffs/issue-AR-199.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: worklog
commit: f03fcfa
short: f03fcfa
date: 2026-07-29
pr: null
related_issues:
  - docs/roadmap/issue-AR-199-restore-codex-workforce-evidence.md
---

# Worklog detail: Expose Codex canary reconcile rejection

## Purpose

Identify the exact strict PostToolUse guard rejecting an otherwise complete
real-child activation chain without capturing callback content.

## Approach

Each reconciliation rejection returns one fixed allowlisted reason. Only the
restricted activation-canary environment emits that code, and the canary
backend projects it only when stderr contains exactly one supported reason.
Raw stderr, prompts, tool arguments, paths, tokens, and ambiguous reasons are
discarded.

## Evidence

Trace `019faee3-7adf-7db0-b358-f74ffb3e5e51` proved the activation grant,
consumption, and specialist load retained the exact planned unit, version,
prompt hash, and real child UUID while the delegation remained synthetic.

## Verification

- All 18 tests in `tests/test_codex_activation_canary.py` passed.
- Ruff check and format passed for the changed Python files.
- Documentation validation passed for 521 Markdown files.

## Follow-ups

Refresh Codex from this checkpoint, capture the one fixed rejection code, and
repair only that evidenced boundary before requiring a live attestation.
