---
title: "Claim Codex spawn execution at the first complete callback"
status: accepted
category: decisions
created: 2026-08-02
updated: 2026-08-02
tags: [codex, delegation, execution, lifecycle, evidence]
related:
  - docs/roadmap/issue-AR-223-prove-codex-child-task-execution.md
  - docs/roadmap/handoffs/issue-AR-207.md
  - docs/decisions/0143-execute-codex-specialists-in-the-initial-spawn-turn.md
  - agency_runtime/adapters/hooks.py
  - tests/test_codex_activation_canary.py
  - docs/worklog/README.md
supersedes:
  - docs/decisions/0143-execute-codex-specialists-in-the-initial-spawn-turn.md
superseded_by: null
id: ADR-0144
type: decision
deciders: [maintainers]
---

# ADR-0144: Claim Codex spawn execution at the first complete callback

## Context

ADR-0143 correctly moved current Codex specialist work into the initial
`spawn_agent` turn, but assumed that `SubagentStart` precedes `PostToolUse`.
Exact installed build `b6bcdfb` proved the reverse order: the parent spawn
result was durable before the real child UUID and activation consumption.
`PostToolUse` recorded a synthetic delegation but could not claim execution;
`SubagentStart` later promoted the exact delegation and loaded the specialist
without claiming the deferred dispatch. The specialist ran, but the Store
retained neither the dispatch receipt nor terminal lifecycle evidence.

Both callback orders are valid host behavior. Neither callback alone is proof:
Agency needs the exact recorded spawn delegation, consumed native-hook grant,
real child identity, and original spawn tool-use ID together.

## Decision

1. Current Codex specialists continue to execute their exact work unit in the
   initial `spawn_agent` turn with no execution follow-up.
2. Agency claims the one-use Store execution dispatch at the first callback
   where both the exact spawn delegation and real activated child identity are
   present. `PostToolUse` claims when `SubagentStart` came first;
   `SubagentStart` claims when `PostToolUse` came first.
3. The claim uses the persisted native-hook assignment's exact tool-use ID and
   remains idempotent for callback replay. A suggested row, synthetic child,
   mismatched delegation, or absent activation cannot create the receipt.
4. Parent `Stop` still requires exact rollout completion before closing the
   worker. A dispatch receipt is authority to execute, not proof of outcome.

## Consequences

- Current Codex callback ordering no longer leaves a real specialist execution
  uncertified merely because the host delivered `PostToolUse` first.
- The reverse synthetic order remains supported without prematurely binding a
  worker before the spawn delegation exists.
- The activation canary can validate the same Store chain used by the product:
  one spawn, one activated real child, one dispatch receipt, and one terminal
  completion.

## Alternatives

- **Claim only in `PostToolUse`.** Rejected by the exact `b6bcdfb` activation.
- **Claim only in `SubagentStart`.** Rejected because some hosts/tests deliver
  child start before the parent delegation is recorded.
- **Infer a fixed callback order.** Rejected because order is host-owned and
  the required evidence can be joined without predicting it.
