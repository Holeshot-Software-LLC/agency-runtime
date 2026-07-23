---
title: "Active recovery capsules"
status: active
category: roadmap
created: 2026-07-23
updated: 2026-07-23
tags: [handoff, context, codex, governance, recovery]
related:
  - AGENTS.md
  - scripts/context_handoff_status.py
  - scripts/verify_docs.py
  - docs/roadmap/issue-AR-126-bounded-idempotent-context-handoffs.md
  - docs/decisions/0085-continue-in-task-after-context-checkpoints.md
supersedes: []
superseded_by: null
---

# Active recovery capsules

An active recovery capsule is the bounded bootstrap projection for one
long-running roadmap item. The canonical issue keeps the full planning and
evidence history; the capsule contains only the current checkpoint, completed
evidence needed for the next decision, exact blocker, next bounded package,
verification commands, and prohibitions.

## Format

Active capsules live at
docs/roadmap/handoffs/issue-AR-NN-description.md and use type: handoff.
Each capsule carries:

- the stable internal issue_id;
- the fixed 50 percent hard-checkpoint threshold and 65 percent live-evaluation
  admission threshold;
- the expected branch;
- the substantive evidence commit and minimum ledger commit already contained
  by the branch;
- the same tracker URL as the canonical issue; and
- links to the canonical issue, latest worklog, and governing decision.

The body must contain Checkpoint, Completed evidence, Exact blocker, Same-task
continuity, Next bounded work package, Verification, and Constraints sections.
One issue may have only one active capsule. A capsule is replaced as the
package advances; it is never an append-only task transcript.

The command python scripts/verify_docs.py rejects a capsule over 12 KiB or 180
lines, duplicate active capsules, missing recovery sections, malformed
checkpoint metadata, threshold drift, tracker drift, and a missing canonical
issue link.

## Telemetry and same-task continuity

Run:

~~~text
python scripts/context_handoff_status.py --json --threshold 50 --admission-threshold 65
~~~

after bootstrap, immediately before every live evaluation, and at package
closeout. A conditional rerun or full-corpus run is a separate admission
decision and requires another immediately preceding check. Below 65 percent,
do not start an expensive live evaluation. At or below 50 percent, first make
the smallest safe in-progress slice a clean durable checkpoint, then continue
in the same task. The 65-percent admission gate already prevents new live
evaluation below that point.

Telemetry is cumulative and normal Codex compaction does not promise a reset.
Never busy-loop, emit empty continuation turns, or wait for the percentage to
rise. A threshold crossing never creates, forks, dispatches, pauses for, or
transfers work to another task. After the clean checkpoint, continue with
normal same-task behavior.

## Active capsules

- [AR-119 inference-first workforce](issue-AR-119.md)
