---
title: "AR-126: Keep context checkpoints in the current task"
status: in_progress
category: roadmap
created: 2026-07-23
updated: 2026-07-23
tags: [governance, documentation, codex, context, reliability]
related:
  - AGENTS.md
  - scripts/context_handoff_status.py
  - scripts/verify_docs.py
  - tests/test_context_handoff_status.py
  - tests/test_verify_docs_schema.py
  - docs/roadmap/handoffs/README.md
  - docs/roadmap/handoffs/issue-AR-119.md
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/decisions/0084-bounded-recovery-capsules-and-idempotent-task-dispatch.md
  - docs/decisions/0085-continue-in-task-after-context-checkpoints.md
supersedes: []
superseded_by: null
type: issue
epic: documentation
issue_id: AR-126
priority: p0
tracker_url: null
depends_on: []
blocks: []
---

# AR-126: Keep context checkpoints in the current task

## Problem

Two Codex task-creation calls reported a missing handler while still creating
receivers, and a fallback created a third receiver on the same branch. A later
receiver did not inherit the source task's persistent goal. The custom
cross-task protocol therefore duplicated coordination state while relying on
goal transfer that Codex does not provide.

The useful parts of the experiment were independent of task creation: a
65-percent admission gate protects expensive live evaluation, a 50-percent
boundary forces a clean durable checkpoint, and a bounded capsule preserves
the current recovery state.

## Current state

All duplicate receivers were stopped before live evaluation and archived.
ADR-0085 supersedes the task-dispatch and goal-transfer design. Repository
policy now retains only the bounded capsule, the separate 65-percent live
admission and 50-percent checkpoint meanings, and immediately-preceding
telemetry for every live run. After a checkpoint, work continues in the same
task through normal Codex behavior.

Tracker creation and label parity remain pending explicit authorization for the
outward-facing write.

## Approach

Keep complete history in canonical roadmap and worklog records while projecting
the current recovery state into one size-bounded active capsule per long-running
issue. Validate capsule identity, size, required sections, canonical issue link,
tracker parity, and the fixed gate values.

Below 65 percent, forbid a new expensive live evaluation. At or below 50
percent, require a clean durable checkpoint and then continue in the same task.
Remove task-creation tokens, task-owner IDs, receiver bootstrap, transfer
proofs, dispatch reconciliation, and threshold-driven waits. Normal Codex
compaction owns context management.

## Dependencies

ADR-0085 supersedes ADR-0084 and defines same-task continuation. AR-119
supplies the reproduced failure and first active capsule.

## Acceptance

- [x] AGENTS.md retains the 65-percent live gate and 50-percent clean
  checkpoint while requiring same-task continuation.
- [x] Documentation validation rejects oversized, incomplete, duplicate, or
  tracker-divergent active recovery capsules.
- [x] Focused tests cover valid and invalid checkpoint metadata and duplicate
  active capsules.
- [x] AR-119 has one current capsule under the enforced size and line limits.
- [x] Telemetry distinguishes the fixed 50-percent hard checkpoint from the
  65-percent expensive-live-evaluation admission gate.
- [x] AGENTS.md requires telemetry after bootstrap and immediately before every
  live evaluation, including conditional second runs.
- [x] The helper and capsule schema contain no task-owner or task-creation
  fields.
- [x] Threshold crossings never create, fork, dispatch, transfer, acknowledge,
  stop for, or wait on another task.
- [ ] A same-repository tracker issue titled with AR-126 and labeled
  epic:documentation is created and mapped after authorization.
