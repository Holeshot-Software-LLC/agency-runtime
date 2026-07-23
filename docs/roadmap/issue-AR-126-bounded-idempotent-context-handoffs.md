---
title: "AR-126: Make autonomous context handoffs bounded and idempotent"
status: in_progress
category: roadmap
created: 2026-07-23
updated: 2026-07-23
tags: [governance, documentation, codex, handoff, reliability]
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

# AR-126: Make autonomous context handoffs bounded and idempotent

## Problem

Two Codex task-creation calls reported a missing handler while still creating
receivers. A fallback created a third receiver on the same branch. After the
duplicates were paused, the retained receiver's required complete read of the
2,379-line AR-119 history reduced remaining context from 84.1 percent to 26.0
percent before work, immediately triggering another handoff. The protocol could
therefore duplicate writers or recurse forever without advancing the issue.

A later recovery exposed the complementary same-chat failure. The receiver did
not inherit the source's persistent goal, and after goal ownership was repaired,
automatic continuations retained cumulative telemetry below the hard checkpoint
instead of creating a reset boundary. Ending again produced empty turns rather
than compaction or progress.

## Current state

All duplicate receivers were stopped before live evaluation and archived. The
bounded capsule, create-once reconciliation, and no-op relay rules are already
enforced. This repair adds persistent goal ownership, separate 65-percent live
admission and 50-percent checkpoint meanings, immediately-preceding telemetry
for every live run, and an explicit rule that cumulative telemetry never causes
an empty wait-for-reset continuation.

Tracker creation and label parity remain pending explicit authorization for the
outward-facing write.

## Approach

Keep complete history in canonical roadmap and worklog records while projecting
the current recovery state into one size-bounded active capsule per long-running
issue. Validate capsule identity, size, required sections, canonical issue link,
and tracker parity in the documentation gate.

Keep the current task as persistent goal owner and sole writer across same-chat
continuations and compactions. Below 65 percent, forbid a new expensive live
evaluation. At or below 50 percent, require a clean durable checkpoint before
further work, prohibit cross-task dispatch, and permit only bounded non-live
recovery or governance work required to repair or close the protocol. Never
busy-loop waiting for cumulative telemetry to reset.

Allow cross-task goal transfer only with explicit user authorization, proof that
the source goal is inactive or its task archived, receiver-side goal creation,
an acknowledgment naming `goal_owner_task_id`, and a clean sole-writer lease.
Retain create-once reconciliation only for that exceptional authorized path.

## Dependencies

ADR-0084 defines the bounded capsule, idempotent dispatch, and no-op recovery
rules. AR-119 supplies the reproduced failure and first active capsule.

## Acceptance

- [x] AGENTS.md defines bounded bootstrap, create-once reconciliation,
  ownership finalization, and no-op relay prohibitions.
- [x] Documentation validation rejects oversized, incomplete, duplicate, or
  tracker-divergent active recovery capsules.
- [x] Focused tests cover valid and invalid handoff metadata and duplicate
  active capsules.
- [x] AR-119 has one current capsule under the enforced size and line limits.
- [x] Telemetry distinguishes the fixed 50-percent hard checkpoint from the
  65-percent expensive-live-evaluation admission gate.
- [x] AGENTS.md requires telemetry after bootstrap and immediately before every
  live evaluation, including conditional second runs.
- [x] Same-chat persistent-goal continuation remains in the owning task below
  the hard checkpoint and never waits in empty turns for cumulative reset.
- [x] Capsule validation requires exact gate values, a goal-owner task UUID,
  and an explicit Goal ownership section.
- [x] Cross-task transfer is fail-closed unless every authorization, source-goal,
  receiver-goal, acknowledgment, and sole-writer condition is proven.
- [ ] A same-repository tracker issue titled with AR-126 and labeled
  epic:documentation is created and mapped after authorization.
- [ ] A later explicitly authorized real goal transfer demonstrates exactly one
  receiver and preserves the goal-owner and sole-writer invariants.
