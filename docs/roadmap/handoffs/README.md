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
  - docs/decisions/0084-bounded-recovery-capsules-and-idempotent-task-dispatch.md
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
- a package-specific handoff_token prefixed by that ID;
- the UUID of the persistent goal-owning task;
- the fixed 50 percent hard-checkpoint threshold and 65 percent live-evaluation
  admission threshold;
- the expected branch;
- the substantive evidence commit and minimum ledger commit already contained
  by the branch;
- the same tracker URL as the canonical issue; and
- links to the canonical issue, latest worklog, and governing decision.

The body must contain Checkpoint, Completed evidence, Exact blocker, Goal
ownership, Next bounded work package, Verification, and Constraints sections.
One issue may have only one active capsule. A capsule is replaced as the
package advances; it is never an append-only task transcript.

The command python scripts/verify_docs.py rejects a capsule over 12 KiB or 180
lines, duplicate active capsules or tokens, missing recovery sections,
malformed checkpoint or goal-owner metadata, threshold drift, tracker drift,
and a missing canonical issue link.

## Telemetry and goal ownership

The persistent goal stays attached to one task, and that task remains the sole
repository writer across automatic continuation or compaction. Run:

~~~text
python scripts/context_handoff_status.py --json --threshold 50 --admission-threshold 65
~~~

after bootstrap, immediately before every live evaluation, and at package
closeout. A conditional rerun or full-corpus run is a separate admission
decision and requires another immediately preceding check. Below 65 percent,
do not start an expensive live evaluation. At or below 50 percent, first make
the smallest safe in-progress slice a clean durable checkpoint, then continue
only bounded non-live recovery or governance work in the same goal-owning
task.

Telemetry is cumulative and automatic continuation does not promise a reset.
Never busy-loop, emit empty continuation turns, or wait for the percentage to
rise. If actual context retention degrades, stop at the clean checkpoint and
report the concrete user action needed; do not create another task.

## Exceptional cross-task transfer

Cross-task goal transfer is exceptional. It is permitted only when explicit
user authorization, an inactive or archived source goal, receiver goal
creation, and a sole-writer acknowledgment naming the capsule's exact
goal_owner_task_id are all proven. If any condition is missing, stop at the
clean checkpoint without creating a task.

Only after those transfer conditions hold, use the capsule's exact
handoff_token in the task-creation prompt and list recent tasks for that token
before creating anything. Call task creation once. If creation times out or
reports an ambiguous error, reconcile the recent task list before retrying.
One matching task is the receiver even if the create call reported failure.
Multiple matches are paused before edits; retain one only after proving the
repository is unchanged and archive the duplicates.

The dispatch prompt adds runtime-only facts that do not belong in Git: the
source task ID and the exact current clean HEAD. It must not require a complete
reread of the canonical issue's historical body.

## Receiver bootstrap

The receiver reads AGENTS.md, this capsule, the live tracker issue, and the
latest linked worklog completely. It consults only the canonical issue sections
or historical evidence named by the capsule, verifies that the clean branch
contains the minimum ledger commit, creates the authorized receiver goal,
checks context telemetry again, and acknowledges sole-writer ownership with
the exact goal_owner_task_id before editing. It repeats telemetry immediately
before any admitted live evaluation.

If bootstrap alone reaches the hard checkpoint, the receiver preserves or
finishes the smallest safe clean checkpoint and continues only bounded
non-live recovery work if retention remains sound. It does not write a
telemetry-only note, manufacture an empty recovery commit, dispatch another
task, or wait in empty turns for cumulative telemetry to reset.

## Active capsules

- [AR-119 inference-first workforce](issue-AR-119.md)
