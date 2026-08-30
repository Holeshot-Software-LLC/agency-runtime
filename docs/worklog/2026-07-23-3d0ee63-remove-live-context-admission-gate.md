---
title: "Worklog detail: Remove live context admission gate"
status: active
category: worklog
created: 2026-07-23
updated: 2026-07-23
tags: [governance, context, codex, reliability]
related:
  - AGENTS.md
  - docs/decisions/0086-use-checkpoint-only-context-telemetry.md
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-126-bounded-idempotent-context-handoffs.md
  - scripts/context_handoff_status.py
supersedes: []
superseded_by: null
type: worklog
commit: 3d0ee636f8f7451ca0e88d354ae9c8fd6b5a4691
short: 3d0ee63
date: 2026-07-23
pr: null
related_issues:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-126-bounded-idempotent-context-handoffs.md
---

# Worklog detail: Remove live context admission gate

## Purpose

Remove the 65-percent live-evaluation admission rule that could indefinitely
block a cleanly checkpointed persistent goal when cumulative Codex telemetry
did not reset. Preserve the useful 50-percent clean-checkpoint behavior and
same-task continuation.

## Approach

ADR-0086 supersedes the live-admission portion of ADR-0085. The telemetry
helper now reports only whether a clean checkpoint must be ensured, the active
capsule schema rejects the removed admission field, and active AR-119/AR-126
contracts state that context percentage never admits or blocks live work.
Focused tests assert the smaller JSON contract and the exact 50-percent
boundary.

## Challenges encountered

The restricted Windows token could not initialize the normal patch wrapper
with the configured writable-root split. The same patch was applied through the
installed Codex patch entry point; no direct file rewrite or destructive Git
operation was used.

## Decisions and alternatives

The durable rationale and rejected alternatives are recorded in
[ADR-0086](../decisions/0086-use-checkpoint-only-context-telemetry.md).
Historical worklogs and superseded decisions retain the former rule for
faithful provenance.

## Verification

- Focused telemetry and documentation-schema tests passed 33/33.
- Ruff check and format-check passed for all four changed Python files.
- Metadata validation passed for 317 Markdown documents.
- Policy availability, worklog-current, and full documentation validation
  passed; documentation validation covered 317 Markdown files.
- `git diff --check` passed.
- Live telemetry emitted `continue_same_task` with no admission fields.

## Follow-ups

- Continue AR-119 with the already prepared instrumented two-case matched
  selection package.
- AR-126 tracker creation remains pending explicit authorization.
