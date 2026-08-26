---
title: "Active recovery capsules"
status: active
category: roadmap
created: 2026-07-23
updated: 2026-07-30
tags: [handoff, context, codex, governance, recovery]
related:
  - AGENTS.md
  - scripts/context_handoff_status.py
  - scripts/verify_docs.py
  - docs/roadmap/issue-AR-126-bounded-idempotent-context-handoffs.md
  - docs/decisions/0086-use-checkpoint-only-context-telemetry.md
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
- the fixed 50 percent clean-checkpoint threshold;
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
issue link. It also rejects the removed live-admission field.

## Telemetry and same-task continuity

Run:

~~~text
python scripts/context_handoff_status.py --json --threshold 50
~~~

after bootstrap, immediately before every live evaluation, and at package
closeout. A conditional rerun or full-corpus run requires another immediately
preceding check. At or below 50 percent, ensure the smallest safe in-progress
slice is represented by a clean durable checkpoint, then continue in the same
task, including live work. The percentage is observational for live evaluation;
it neither admits nor blocks the run.

Telemetry is cumulative and normal Codex compaction does not promise a reset.
Never busy-loop, emit empty continuation turns, or wait for the percentage to
rise. Reuse an existing clean recovery checkpoint when there is no substantive
delta rather than creating an empty commit pair. A threshold crossing never
creates, forks, dispatches, pauses for, blocks live work, or transfers work to
another task. After the clean checkpoint, continue with normal same-task
behavior.

## Active capsules

- [AR-119 inference-first workforce](issue-AR-119.md)
- [AR-180 Codex 0.149 hook compatibility](issue-AR-180.md)
- [AR-189 ownership-bound host uninstall](issue-AR-189.md)
- [AR-190 uv-tool upgrade planning](issue-AR-190.md)
- [AR-196 dashboard-service two-phase activation](issue-AR-196.md)
- [AR-199 Codex workforce evidence restoration](issue-AR-199.md)
- [AR-200 diagnosable decision conformance](issue-AR-200.md)
- [AR-201 default workforce repair budget](issue-AR-201.md)
- [AR-204 README-story contract reconciliation](issue-AR-204.md)
- [AR-205 inference-safe exact specialist staffing](issue-AR-205.md)
- [AR-207 preflight and delegation failure diagnostics](issue-AR-207.md)
- [AR-264 actionable contractor execution profiles](issue-AR-264.md)
- [AR-265 contextual turn classification](issue-AR-265.md)
- [AR-289 native reranker transports](issue-AR-289.md)
- [AR-290 end-to-end guided setup](issue-AR-290.md)
- [AR-297 complete unattended container bootstrap](issue-AR-297.md)
