---
title: "Worklog: Enforce persistent goal context continuity"
status: active
category: worklog
created: 2026-07-23
updated: 2026-07-23
tags: [governance, handoff, context, codex, reliability]
related:
  - AGENTS.md
  - scripts/context_handoff_status.py
  - scripts/verify_docs.py
  - tests/test_context_handoff_status.py
  - tests/test_verify_docs_schema.py
  - docs/roadmap/issue-AR-126-bounded-idempotent-context-handoffs.md
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/handoffs/issue-AR-119.md
  - docs/decisions/0084-bounded-recovery-capsules-and-idempotent-task-dispatch.md
supersedes: []
superseded_by: null
type: worklog
commit: b927266f9fa5bee108f4d54f0a80e910eaabaebe
short: b927266
date: 2026-07-23
pr: null
related_issues:
  - docs/roadmap/issue-AR-126-bounded-idempotent-context-handoffs.md
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
---

# Worklog: Enforce persistent goal context continuity

## Purpose

Repair the autonomous recovery protocol after two observed failure modes: a
new task did not inherit the source task's persistent goal, and automatic
same-chat continuation retained cumulative telemetry below the hard checkpoint
instead of creating a reset boundary. The former could split ownership; the
latter produced empty turns without advancing work.

## Approach

Repository instructions, ADR-0084, AR-126, and capsule guidance now keep one
persistent goal owner and sole repository writer across automatic continuation
or compaction. Telemetry has two explicit meanings: 65 percent is the admission
gate for a new expensive live evaluation, while 50 percent is the hard reserve
that requires a clean durable checkpoint before bounded non-live recovery or
governance work continues.

The telemetry helper reports both decisions and a deterministic action that
never requests waiting for a reset. The documentation validator now requires
the exact gate values, a lowercase goal-owner task UUID, and a Goal ownership
section in every active capsule. The AR-119 capsule records the current owner
and preserves the unchanged complete-corpus package without admitting it under
low telemetry.

## Challenges encountered

The existing `handoff_required` field represented only the 50-percent boundary,
so removing it would have broken callers while still failing to express the
separate live admission decision. It remains as a compatibility alias for the
hard-checkpoint result; the new fields and `protocol_action` carry the precise
semantics.

Documentation validation correctly rejected the capsule's forward link to this
worklog before the substantive SHA existed. The ledger commit creates the
detail file and reciprocal traceability after the substantive commit, matching
the repository's finite self-recording protocol.

## Decisions and alternatives

At or above 65 percent, a live evaluation may be admitted. Below 65 percent,
each new live run—including a conditional rerun or full corpus—is prohibited
until a fresh telemetry check admits it. At or below 50 percent, cross-task
dispatch is prohibited and only bounded non-live recovery or governance work
may follow a clean checkpoint in the same goal-owning task.

Cross-task goal transfer remains exceptional and fail-closed: explicit user
authorization, an inactive source goal or archived source task, receiver goal
creation, an acknowledgment naming `goal_owner_task_id`, and a clean sole-writer
lease must all be proven. Empty continuations and speculative receiver creation
were rejected because cumulative telemetry is not promised to reset.

## Verification

- Focused telemetry and capsule-schema tests passed: 34 tests.
- Ruff check and format validation passed for the four modified Python files.
- Metadata validation covered 312 Markdown documents.
- Policy availability and worklog pre-commit checks passed.
- Documentation validation and Git whitespace validation passed.
- No live evaluation, cross-task dispatch, tracker mutation, push, PR, or hosted
  Actions run was performed.

## Follow-ups

AR-119 still requires the unchanged complete 19-case matched-selection corpus,
but it may start only after an immediately preceding telemetry check reports at
least 65 percent remaining. AR-126 still requires authorized tracker parity and
a later explicitly authorized real goal-transfer proof; neither is inferred
from this local governance repair.
