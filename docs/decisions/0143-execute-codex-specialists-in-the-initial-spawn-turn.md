---
title: "Execute Codex specialists in the initial spawn turn"
status: superseded
category: decisions
created: 2026-08-02
updated: 2026-08-02
tags: [codex, delegation, execution, lifecycle, evidence]
related:
  - docs/roadmap/issue-AR-223-prove-codex-child-task-execution.md
  - docs/roadmap/handoffs/issue-AR-207.md
  - docs/decisions/0128-persist-exact-codex-plan-authority-and-serialize-launches.md
  - docs/decisions/0137-reconcile-codex-followup-completion-at-parent-stop.md
  - docs/decisions/0139-make-codex-execution-turns-self-contained.md
  - docs/decisions/0141-admit-writer-proof-only-through-agency-plans.md
  - docs/decisions/0142-require-terminal-product-child-before-next-unit.md
  - agency_runtime/adapters/hooks.py
  - agency_runtime/core/codex_child_execution.py
  - agency_runtime/core/evals/product_host.py
  - agency_runtime/core/native_child_prompt_delivery.py
  - tests/test_codex_activation_canary.py
  - tests/test_codex_child_execution.py
  - docs/worklog/README.md
supersedes:
  - docs/decisions/0137-reconcile-codex-followup-completion-at-parent-stop.md
  - docs/decisions/0139-make-codex-execution-turns-self-contained.md
  - docs/decisions/0142-require-terminal-product-child-before-next-unit.md
superseded_by: docs/decisions/0144-claim-codex-spawn-execution-at-the-first-complete-callback.md
id: ADR-0143
type: decision
deciders: [maintainers]
---

# ADR-0143: Execute Codex specialists in the initial spawn turn

## Context

Agency introduced an activation-only first child turn followed by an encrypted
`followup_task` execution turn because an earlier Codex child acknowledged its
spawn without creating the required artifact. Exact installed build `bffd2c8`
then proved that the completed two-turn ceremony still produced no workspace
artifact. The additional turn was therefore ceremony, not execution proof.

A direct native Codex child was subsequently given the same bounded writer
goal in its initial `spawn_agent` message. That one turn created and read back
the exact workspace sentinel. Its retained parent and child rollouts expose one
parent spawn ciphertext, the byte-identical child `NEW_TASK` ciphertext, exact
parent-child lineage, one started and completed child turn, and one nonempty
final response. Current Codex therefore provides enough evidence to bind the
spawn itself to first-turn specialist execution.

The Store delegation row does not exist at `SubagentStart`; it is recorded when
the parent `PostToolUse` hook observes the completed spawn. The direct execution
claim must consequently be bound after that hook records the delegation, using
the exact consumed native-hook spawn receipt when the callback omits its tool
identifier.

## Decision

1. A current Codex specialist receives its exact persisted work-unit goal and
   specialist context in the initial `spawn_agent` turn and executes that goal
   immediately. The child must not redelegate, broaden the goal, or return a
   readiness-only acknowledgement.
2. The parent calls `spawn_agent` exactly once per dependency-ready row, then
   waits up to three bounded times for that same child to become terminal. It
   never sends an execution `followup_task` and never launches the next row
   before the prior child is terminal.
3. Direct execution evidence requires exact parent session identity, exact
   spawn call identity and arguments, exact task name, one parent-child lineage,
   one child turn, byte-identical spawn and child `NEW_TASK` ciphertext, and one
   nonempty final response before child completion.
4. The direct Store execution dispatch is claimed only after `PostToolUse` has
   recorded the corresponding delegation. If the callback omits the tool-use
   identifier, Agency reads the sole exact consumed Codex spawn receipt for the
   same session, trace, unit, worker, and native run.
5. Historical version-1 and version-2 activation/follow-up evidence remains
   readable for retained trials. It is compatibility evidence only and is not
   emitted by the current Codex product path.

## Consequences

- Current Codex product execution uses one child turn instead of two and removes
  one activation wait and one follow-up call from every planned row.
- The product and activation rollout projections admit the direct spawn-plus-
  terminal-wait topology while retaining strict causal, cardinality, lineage,
  ciphertext, and completion checks.
- A second follow-up for a current direct child is denied because the spawn has
  already consumed the exact execution dispatch authority.
- A terminal child still does not prove a workspace mutation. Product success
  continues to require the exact workspace-write artifact defined by AR-223.

## Alternatives

- **Keep the activation-only and follow-up turns.** Rejected because the exact
  installed trial completed that protocol without producing an artifact, while
  the direct native first turn wrote successfully.
- **Treat any completed child as execution proof.** Rejected because completion
  without exact spawn ciphertext, lineage, and final-response evidence would
  repeat the false-positive boundary already observed.
- **Let the parent perform missing product work.** Rejected because it would
  conceal specialist execution failure and violate the accepted Agency plan.
