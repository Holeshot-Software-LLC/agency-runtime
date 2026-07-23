---
title: "Worklog: Keep context checkpoints in the current task"
status: active
category: worklog
created: 2026-07-23
updated: 2026-07-23
tags: [governance, context, codex, reliability]
related:
  - AGENTS.md
  - scripts/context_handoff_status.py
  - scripts/verify_docs.py
  - tests/test_context_handoff_status.py
  - tests/test_verify_docs_schema.py
  - docs/roadmap/issue-AR-126-bounded-idempotent-context-handoffs.md
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/handoffs/README.md
  - docs/roadmap/handoffs/issue-AR-119.md
  - docs/decisions/0084-bounded-recovery-capsules-and-idempotent-task-dispatch.md
  - docs/decisions/0085-continue-in-task-after-context-checkpoints.md
supersedes: []
superseded_by: null
type: worklog
commit: 4a19e230c7205a1ca547cfc75d85616d7b634811
short: 4a19e23
date: 2026-07-23
pr: null
related_issues:
  - docs/roadmap/issue-AR-126-bounded-idempotent-context-handoffs.md
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
---

# Worklog: Keep context checkpoints in the current task

## Purpose

Remove the custom context-threshold behavior that created, transferred, or
waited for another Codex task. Persistent goals are task-local, and ambiguous
task creation had already produced duplicate receivers. Retain the useful
65-percent expensive-live-work gate and 50-percent clean-checkpoint boundary.

## Approach

ADR-0085 supersedes ADR-0084's task-dispatch and goal-transfer design.
`AGENTS.md` now requires a clean substantive/ledger checkpoint at or below 50
percent and then continues the current task through normal Codex behavior.
Thresholds never create, fork, dispatch, pause for, or transfer work to another
task.

The telemetry helper removes the legacy `handoff_required` alias and reports
`checkpoint_then_continue_same_task` at the hard boundary. Recovery capsules
no longer require task-owner UUIDs, task-creation tokens, receiver
acknowledgments, or transfer sections. Size, single-capsule, tracker parity,
fixed-gate, and bounded current-state validation remain intact.

## Challenges encountered

The earlier commits and worklogs faithfully describe the superseded experiment,
so they were not rewritten. A new ADR and reciprocal superseding links preserve
the decision history while the active policy, capsule, schema, and roadmap
describe the current behavior.

The sandboxed dashboard runner initially failed with `spawn EPERM`; the same
test passed outside that process-spawn restriction. The first unchanged routing
evaluation missed only cache-hit p95 at 2.318 ms against a 2.0 ms gate. One
unchanged rerun passed every gate at 1.633 ms, so no threshold or product code
changed. The full Python matrix did not return output within a 20-minute bound
and was terminated cleanly; that attempt is inconclusive, not a test failure or
pass.

## Decisions and alternatives

Normal Codex compaction owns context management. Repository policy does not
attempt to manufacture a fresh task or transfer chat-local goal state. Removing
the context controls entirely was rejected because the 65-percent live gate and
50-percent checkpoint provide useful evidence and recovery discipline without
cross-task coordination.

The existing recovery-capsule paths and historical `handoff` type remain for
stable repository links. Their active semantics are checkpoint projection, not
task dispatch.

## Verification

- Focused telemetry and capsule-schema tests passed: 34 tests.
- Ruff check passed, and 536 Python files satisfy the formatter.
- Metadata validation and documentation validation passed for 313 Markdown
  documents.
- Policy availability, worklog consistency, and Git whitespace checks passed.
- Dashboard UI tests passed 97/97 outside the spawn-restricted sandbox.
- One unchanged routing rerun passed all routing, policy, delegation, and
  performance gates after the first run's isolated cache-hit latency miss.
- The full Python matrix exceeded its 20-minute bound without a result and was
  terminated; no full-matrix outcome is claimed.

## Follow-ups

AR-119 continues in the same task after every clean checkpoint. Its unchanged
complete 19-case live corpus still requires an immediately preceding telemetry
reading of at least 65 percent. AR-126 still needs authorized tracker parity;
no goal-transfer demonstration remains required.
