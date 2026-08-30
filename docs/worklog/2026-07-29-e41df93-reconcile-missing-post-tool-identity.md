---
title: "Worklog detail: Reconcile missing Codex post-tool identity"
status: active
category: worklog
created: 2026-07-29
updated: 2026-07-29
tags: [codex, activation, hooks, correlation, evidence]
related:
  - docs/roadmap/issue-AR-199-restore-codex-workforce-evidence.md
  - docs/roadmap/handoffs/issue-AR-199.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: worklog
commit: e41df93
short: e41df93
date: 2026-07-29
pr: null
related_issues:
  - docs/roadmap/issue-AR-199-restore-codex-workforce-evidence.md
---

# Worklog detail: Reconcile missing Codex post-tool identity

## Purpose

Allow PostToolUse to project lineage that was already authorized by PreToolUse
and consumed against the real SubagentStart child when no usable post-tool
callback identity is available.

## Approach

The reconciliation path no longer requires a second callback ID. It still
requires one consumed native-hook grant, the exact planned task label and
specialist version/hash, Codex's bounded rooted response, and a real
`codex-agent:<UUID>` lineage. Every mismatch remains fail-closed.

## Evidence

Live trace `019faeca-406f-7d20-b2e7-6b1741b5a8af` disproved the preceding
nonempty-ID rewrite hypothesis: the delegation remained synthetic after that
source refresh. The focused regression now omits PostToolUse identity entirely
after exact SubagentStart consumption and requires the real reciprocal links.

## Verification

- All 17 activation-canary tests passed.
- Focused Ruff check and format passed.
- Documentation validation passed for 519 Markdown files.

## Follow-ups

Refresh this clean source checkpoint and rerun the isolated canary.
