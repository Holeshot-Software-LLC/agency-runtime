---
title: "AR-126: Make autonomous context handoffs bounded and idempotent"
status: in_progress
category: roadmap
created: 2026-07-23
updated: 2026-07-23
tags: [governance, documentation, codex, handoff, reliability]
related:
  - AGENTS.md
  - scripts/verify_docs.py
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

## Current state

All duplicate receivers were stopped before live evaluation and archived. One
temporary roadmap paragraph was removed, leaving the branch clean at the prior
ledger checkpoint with no net repository, tracker, or hosted-state mutation.
The existing protocol has telemetry and ownership gates but does not bound
bootstrap input, reconcile ambiguous task creation, or prohibit no-op relay
commits.

Tracker creation and label parity remain pending explicit authorization for the
outward-facing write.

## Approach

Keep complete history in canonical roadmap and worklog records while projecting
the current recovery state into one size-bounded active capsule per long-running
issue. Validate capsule identity, size, required sections, canonical issue link,
and tracker parity in the documentation gate.

Make task dispatch create-once and reconcile-on-error using a stable
package-specific token. Require receiver bootstrap from AGENTS.md, the capsule,
live issue, and latest worklog rather than an unbounded issue reread. Make
preflight context exhaustion a visible blocker at the existing clean
checkpoint, not a reason to create empty commits or another task.

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
- [ ] A same-repository tracker issue titled with AR-126 and labeled
  epic:documentation is created and mapped after authorization.
- [ ] A later real handoff demonstrates exactly one receiver and preserves
  more than half of its context after bounded bootstrap.
