---
title: "Continue in the current task after context checkpoints"
status: superseded
category: decisions
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
supersedes:
  - docs/decisions/0084-bounded-recovery-capsules-and-idempotent-task-dispatch.md
superseded_by: docs/decisions/0086-use-checkpoint-only-context-telemetry.md
id: ADR-0085
type: decision
deciders: [maintainers]
---

# ADR-0085: Continue in the current task after context checkpoints

## Context

The cross-task recovery experiment created duplicate Codex tasks after
ambiguous task-creation errors. It also relied on persistent goal state
transferring to a receiver, but goal state is task-local. Ownership
acknowledgments, transfer proofs, and receiver waits added coordination state
without improving the underlying work.

The 65-percent admission gate for expensive live evaluation and the
50-percent clean-checkpoint boundary remain useful. They reserve enough context
for live evidence capture and ensure that long-running work has a durable
recovery point before context becomes tight.

## Decision

Keep one bounded recovery capsule per long-running roadmap item, the fixed
65-percent live-evaluation admission gate, and the fixed 50-percent clean
checkpoint. At or below 50 percent, finish the smallest safe slice, update the
canonical issue and capsule, run proportionate checks, create the substantive
and ledger commits, and then continue in the same task through normal Codex
behavior.

Context thresholds never create, fork, dispatch, or wait for another task.
They do not pause or transfer a persistent goal, record a task owner, or
require a receiver acknowledgment. The telemetry helper reports only the live
admission and hard-checkpoint decisions; active capsules no longer carry task
IDs or task-creation tokens.

## Consequences

Normal Codex compaction remains responsible for context management. Repository
policy no longer tries to manufacture a fresh context window or transfer
chat-local goal state. Work can continue after every clean checkpoint, while a
new expensive live evaluation remains prohibited unless its immediately
preceding telemetry reading is at least 65 percent.

The recovery capsule remains useful as a compact current-state projection, but
it is not a task-dispatch contract. Historical worklogs continue to describe
the superseded experiment faithfully.

## Alternatives

Automatically creating a new task at a threshold was rejected because creation
can be ambiguous and goals do not transfer. Keeping an exceptional transfer
protocol was rejected because it preserves the same coordination failure in a
less common path. Removing the live gate and clean checkpoint was rejected
because both controls protect expensive evidence collection and durable
recovery without requiring another task.
