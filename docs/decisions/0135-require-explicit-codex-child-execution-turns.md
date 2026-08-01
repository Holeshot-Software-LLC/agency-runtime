---
title: "Require explicit Codex child execution turns"
status: accepted
category: decisions
created: 2026-08-01
updated: 2026-08-01
tags: [codex, delegation, execution, activation, evidence]
related:
  - docs/roadmap/issue-AR-223-prove-codex-child-task-execution.md
  - docs/roadmap/handoffs/issue-AR-207.md
  - docs/decisions/0094-durable-native-child-correlation.md
  - docs/decisions/0128-persist-exact-codex-plan-authority-and-serialize-launches.md
  - agency_runtime/core/codex_child_execution.py
  - agency_runtime/core/canary_backends.py
  - agency_runtime/core/evals/product_host.py
  - tests/test_codex_activation_canary.py
  - tests/test_codex_child_execution.py
  - docs/worklog/README.md
supersedes: []
superseded_by: null
id: ADR-0135
type: decision
deciders: [maintainers]
---

# ADR-0135: Require explicit Codex child execution turns

## Context

Exact merged build `43870c8` proved native Codex child activation, specialist
injection, current wait handling, and terminal child lifecycle for every
accepted product work unit. Its governed product trial nevertheless left the
isolated workspace empty. The initial `spawn_agent` message can create a child
whose first turn acknowledges the inter-agent message and completes without
performing the requested work. A successful spawn turn is therefore activation
evidence, not execution evidence.

Codex exposes `followup_task` as the supported way to send a message to an
existing child and trigger another turn. The child rollout records exact turn
boundaries, tool calls, and completion events, so Agency can prove that the
execution envelope occurred in the later turn without retaining the user's
task or the child's response. Current Codex encrypts collaboration message
arguments before both `PreToolUse` and the persisted parent rollout observe
them; only the receiving child's rollout exposes the decrypted message.

## Decision

For every governed Codex work unit:

1. `spawn_agent` carries the exact canonical Agency context and declares its
   first child turn activation-only. The child performs no work or tools in
   that turn and returns one bounded readiness acknowledgement.
2. After the first terminal wait, the parent calls `followup_task` exactly once
   on that child with the exact canonical execution envelope generated for the
   accepted plan row. A second wait observes the execution turn. The parent
   cannot use `send_message`, reuse a child, retry delivery, or do specialist
   work itself.
3. Because the parent boundary is opaque, `PreToolUse` binds the encrypted
   message shape and exact canonical child path to one activated plan row. The
   Store atomically claims that dispatch once against the exact trace,
   work-unit ID, native task name, child identity, goal hash, and follow-up
   tool-use ID. An exact replay of the same tool-use ID is idempotent; a
   different claim is denied.
4. A passed worker outcome requires a later child turn whose bounded rollout
   contains exactly that execution envelope between its own `task_started` and
   `task_complete` events. The earlier activation completion cannot pass the
   worker. Missing, duplicate, reordered, cross-child, malformed, or
   link-unsafe evidence fails closed.
5. Activation proof contract `agency.codex-activation-canary.v2` and product
   proof both require the exact `spawn_agent`, `wait_agent`, `followup_task`,
   `wait_agent` sequence. Older activation attestations remain historical and
   stale for this execution contract.

## Consequences

- Codex child activation and task execution are separate, observable lifecycle
  facts. A green child exit alone cannot claim that specialist work occurred.
- Each accepted Codex plan row receives exactly one actionable execution turn,
  while the existing one-at-a-time scheduler and least-privilege mutation scope
  remain unchanged.
- Schema version 43 records the content-free follow-up tool-use ID and dispatch
  timestamp on the worker run. It does not store the task or response text.
- Parent ciphertext is lifecycle evidence only. The exact decrypted execution
  envelope remains mandatory in the causally later child turn.
- Live activation and product evidence must now prove two causal child turns
  per unit. This adds one follow-up and one wait to each Codex child execution.

## Alternatives

- **Treat the initial spawn completion as execution.** Rejected because the
  exact product trial proved that it can terminate without any required work.
- **Repeat the original spawn.** Rejected because that creates a second child
  and duplicate-work risk instead of addressing the activated worker.
- **Send an untracked reminder or retry.** Rejected because it cannot be bound
  to accepted plan authority and makes at-most-once execution unprovable.
- **Let the parent perform missing specialist work.** Rejected because it
  silently restores the generalist path that Agency is intended to replace
  when inference staffing succeeds.
