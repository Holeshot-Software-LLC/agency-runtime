---
title: "Active recovery capsules"
status: active
category: roadmap
created: 2026-07-23
updated: 2026-07-23
tags: [handoff, context, codex, governance, recovery]
related:
  - AGENTS.md
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
- the expected branch;
- the substantive evidence commit and minimum ledger commit already contained
  by the branch;
- the same tracker URL as the canonical issue; and
- links to the canonical issue, latest worklog, and governing decision.

The body must contain Checkpoint, Completed evidence, Exact blocker, Next
bounded work package, Verification, and Constraints sections. One issue may
have only one active capsule. A capsule is replaced as the package advances; it
is never an append-only task transcript.

The command python scripts/verify_docs.py rejects a capsule over 12 KiB or 180
lines, duplicate active capsules or tokens, missing recovery sections,
malformed checkpoint metadata, tracker drift, and a missing canonical issue
link.

## Dispatch

Use the capsule's exact handoff_token in the task-creation prompt and list
recent tasks for that token before creating anything. Call task creation once.
If creation times out or reports an ambiguous error, reconcile the recent task
list before retrying. One matching task is the receiver even if the create call
reported failure. Multiple matches are paused before edits; retain one only
after proving the repository is unchanged and archive the duplicates.

The dispatch prompt adds runtime-only facts that do not belong in Git: the
source task ID and the exact current clean HEAD. It must not require a complete
reread of the canonical issue's historical body.

## Receiver bootstrap

The receiver reads AGENTS.md, this capsule, the live tracker issue, and the
latest linked worklog completely. It consults only the canonical issue sections
or historical evidence named by the capsule, verifies that the clean branch
contains the minimum ledger commit, checks context telemetry again, and
acknowledges sole-writer ownership before editing or live evaluation.

If bootstrap alone reaches the context threshold, the receiver reports the
budget failure and stops at the existing checkpoint. It does not write a
telemetry note, manufacture a recovery commit, or create another task.

## Active capsules

- [AR-119 inference-first workforce](issue-AR-119.md)
