---
title: "Worklog detail: Require a zero-correction Codex canary header"
status: active
category: worklog
created: 2026-07-29
updated: 2026-07-29
tags: [codex, headers, canary, finalization, delegation]
related:
  - docs/roadmap/issue-AR-199-restore-codex-workforce-evidence.md
  - docs/roadmap/handoffs/issue-AR-199.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: worklog
commit: a23f42a
short: a23f42a
date: 2026-07-29
pr: null
related_issues:
  - docs/roadmap/issue-AR-199-restore-codex-workforce-evidence.md
---

# Worklog detail: Require a zero-correction Codex canary header

## Purpose

Make first-pass header correctness an enforced Codex activation gate rather
than accepting a Stop correction as successful proof.

## Approach

A successful native `wait_agent` PostToolUse boundary now returns an
authoritative seven-line header snapshot from the current turn's Store
evidence. Codex receives that snapshot immediately before final response
generation. The activation verifier requires exactly one accepted
finalization, reports `correction_count`, and projects only validated header
fields into the canary report.

## Challenges encountered

Exact-installed trace `019fafb3-8200-7163-83b0-e2405c783a4c` completed the
entire specialist chain but omitted six fields from its first response. The
legacy verifier treated correction-plus-accept as pass, contradicting the
owner's zero-correction acceptance gate.

## Decisions and alternatives

Keep Stop correction as a fail-closed production backstop, but make every
correction a canary failure. Inject the post-wait evidence snapshot instead of
adding more probabilistic prompt emphasis at turn start, where delegation and
specialist completion evidence do not yet exist.

## Verification

- Three exact post-wait, zero-correction, and correction-rejection regressions
  pass.
- The directly affected hook and canary suites pass 148 tests.
- Ruff check, formatting, documentation validation, and diff checks pass.

## Follow-ups

Merge and exact-install this revision, then rerun one isolated activation
canary. The proof requires `correction_count: 0` before moving to the next
AR-199 checklist item.
