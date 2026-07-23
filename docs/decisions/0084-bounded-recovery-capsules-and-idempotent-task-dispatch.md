---
title: "Use bounded recovery capsules and persistent goal ownership"
status: superseded
category: decisions
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
  - docs/roadmap/handoffs/README.md
  - docs/roadmap/handoffs/issue-AR-119.md
  - docs/decisions/0085-continue-in-task-after-context-checkpoints.md
supersedes: []
superseded_by: docs/decisions/0085-continue-in-task-after-context-checkpoints.md
id: ADR-0084
type: decision
deciders: [maintainers]
---

# ADR-0084: Use bounded recovery capsules and persistent goal ownership

## Context

Append-only roadmap evidence can grow beyond a fresh task's safe bootstrap
budget. Requiring a receiver to reread that entire history can cross the
handoff threshold before useful work starts and recursively create more tasks.
Separately, asynchronous task creation can succeed even when its caller sees an
error, so retrying without reconciliation can create concurrent receivers on
one branch.

Persistent goals add a different boundary: goal state is chat-local and does
not automatically transfer to a receiver. Same-chat continuation may also keep
cumulative telemetry instead of resetting it. Empty turns that wait for that
value to rise neither compact context nor advance work.

## Decision

Keep full history in the canonical roadmap and worklog system, and maintain one
validated active recovery capsule for each long-running issue. The capsule is a
replace-in-place projection capped at 12 KiB and 180 lines. It carries a stable
package token, branch, evidence and ledger commits, tracker binding,
`goal_owner_task_id`, fixed 50-percent hard checkpoint and 65-percent live
admission gates, exact blocker, one next package, checks, and constraints.

Run telemetry after bootstrap, immediately before every live evaluation, and at
package closeout. Below 65 percent, do not start a new expensive live run. At or
below 50 percent, first establish a clean checkpoint; then only bounded non-live
recovery or governance work may continue. Cumulative telemetry is not expected
to reset, so the agent never emits an empty turn waiting for a higher value.

An authorized persistent goal remains in the same task across automatic
continuations and compactions; that task remains sole writer. Cross-task goal
transfer is fail-closed unless the user authorizes it, the source goal is paused
or cleared or its task archived, the receiver creates the goal, acknowledges
its task ID, records that owner in the capsule, and proves a clean sole-writer
lease. Only then does create-once, reconcile-on-error dispatch apply.

If actual retention degrades, the owner finishes the smallest safe checkpoint
and reports a concrete user-action blocker. Read-only preflight or cumulative
telemetry alone never creates an empty commit, relay task, or continuation.

## Consequences

Same-task goals preserve one owner and writer without replaying an unbounded
transcript. Separate gates reserve context before live work while allowing
bounded non-live recovery. Exceptional transfer remains reconcilable without
making task creation the normal compaction mechanism. The capsule changes with
package or goal ownership; the canonical issue remains the source of truth.

## Alternatives

Continuing to append every handoff to the canonical issue was rejected because
bootstrap cost grows without bound. Retrying task creation immediately after an
error was rejected because the operation may already have succeeded. Creating
a commit for every read-only preflight was rejected because it advances history
without evidence and feeds the same relay loop. Automatically creating a task
at 50 percent was rejected because chat-local goal ownership can be lost.
Waiting through empty turns for cumulative reset was rejected because no reset
is guaranteed. Relying only on a pasted prompt was rejected because recovery
state would not be independently verifiable from the repository.
