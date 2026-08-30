---
title: "Worklog detail: Resolve Codex post-tool unit from output"
status: active
category: worklog
created: 2026-07-29
updated: 2026-07-29
tags: [codex, hooks, correlation, activation]
related:
  - docs/roadmap/issue-AR-199-restore-codex-workforce-evidence.md
  - docs/roadmap/handoffs/issue-AR-199.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: worklog
commit: cc4ab2f
short: cc4ab2f
date: 2026-07-29
pr: null
related_issues:
  - docs/roadmap/issue-AR-199-restore-codex-workforce-evidence.md
---

# Worklog detail: Resolve Codex post-tool unit from output

## Purpose

Reach the consumed-child reconciliation path when PostToolUse does not preserve
an input-side planned-unit label.

## Approach

Resolve the work unit by matching Codex's validated rooted output task label to
exactly one persisted plan row. Any input label that is present must agree.
Only then may the already-consumed grant and real child UUID be projected.

## Evidence

Trace `019faecf-eb9c-7373-856a-5c7c7cf7d6a3` still retained the synthetic
task lineage after missing-ID reconciliation, proving the work-unit resolver
had not reached the authoritative consumed grant.

## Verification

- All 17 activation-canary tests passed.
- Focused Ruff check and format passed.

## Follow-ups

Refresh this clean checkpoint and rerun the isolated canary.
