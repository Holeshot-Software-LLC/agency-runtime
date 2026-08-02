---
title: "Make Codex execution turns self-contained"
status: accepted
category: decisions
created: 2026-08-01
updated: 2026-08-01
tags: [codex, delegation, execution, context, evidence]
related:
  - docs/roadmap/issue-AR-223-prove-codex-child-task-execution.md
  - docs/roadmap/handoffs/issue-AR-207.md
  - docs/decisions/0135-require-explicit-codex-child-execution-turns.md
  - docs/decisions/0136-bind-opaque-codex-execution-by-ciphertext-identity.md
  - docs/decisions/0137-reconcile-codex-followup-completion-at-parent-stop.md
  - agency_runtime/core/native_child_prompt_delivery.py
  - agency_runtime/core/preflight_recipe.py
  - agency_runtime/core/codex_child_execution.py
  - tests/test_native_child_prompt_delivery.py
  - tests/test_unit_aware_delegation.py
  - docs/worklog/README.md
supersedes:
  - docs/decisions/0136-bind-opaque-codex-execution-by-ciphertext-identity.md
superseded_by: null
id: ADR-0139
type: decision
deciders: [maintainers]
---

# ADR-0139: Make Codex execution turns self-contained

## Context

Exact installed build `eb8e077` proves an accepted nine-unit inferred plan,
seven loaded specialists, nine exact second turns, nine exit-zero workers, one
accepted finalization, a valid first header, and zero corrections. Its three
writer children nevertheless leave the exact product workspace empty. Child
lifecycle and ciphertext identity therefore pass while task realization fails.

The execution follow-up named only the work-unit ID and goal hash, then told
the child to recover the actionable goal from its immediately preceding
activation turn. That made correctness depend on model memory across separate
native child turns. A goal hash can authenticate task identity, but it cannot
tell a model what to do. A native Agency-disabled control made the same mistake
by placing the sentinel details only in parent instructions; its child also
left no sentinel, so that control cannot establish a workspace or sandbox
failure.

## Decision

1. Every actionable Codex execution turn carries the exact hash-bound work-unit
   goal in that same turn. The child never recovers actionable instructions
   from activation-turn memory.
2. The accepted plan projects a canonical execution-message prefix for every
   row. The parent concatenates that prefix with the same exact goal used for
   `spawn_agent`, with no separator or transformation, and sends the result
   once through `followup_task` to the exact activated child.
3. The execution parser recomputes the goal hash and rejects missing, empty,
   appended, altered, or mismatched goal content. Identity-only legacy
   envelopes may be recognized for compatibility but cannot authorize a
   plaintext production dispatch or satisfy plaintext execution proof.
4. Multi-unit context retains one shared goal prefix plus per-row suffixes.
   The parent reconstructs each exact goal once for both spawn and execution,
   keeping the complete accepted plan within Agency's 32,000-character bound
   without duplicating every goal.
5. Current Codex ciphertext identity, Store one-use dispatch claims, ordered
   two-turn lifecycle proof, parent-`Stop` reconciliation, and the non-working
   parent remain mandatory. Ciphertext proves which message crossed the host;
   a real child-created sentinel proves that the message was actionable.

## Consequences

- Activation establishes specialist context; execution independently contains
  everything required to perform one exact work unit.
- A worker can no longer appear actionable merely because its lifecycle and
  content-free identity receipts are complete.
- The first live checkpoint is one isolated writer-child sentinel. A new
  immutable build and full product trial are not spent unless that sentinel
  passes.
- Focused protocol and lifecycle coverage currently passes 164 tests, including
  exact goal/hash binding, tamper rejection, multi-unit reconstruction, and the
  32,000-character context ceiling. This is local code evidence, not live child
  workspace-write evidence.

## Alternatives

- **Continue relying on activation-turn memory.** Rejected because the exact
  product trial proves that valid receipts and exit-zero workers can still
  leave every required artifact absent.
- **Put the full goal in every plan field twice.** Rejected because it needlessly
  expands large inferred plans and can recreate the host-context spill already
  fixed by ADR-0138.
- **Treat exit zero or ciphertext equality as task completion.** Rejected
  because both are transport and lifecycle evidence, not artifact evidence.
- **Let the parent repair missing files.** Rejected because it would conceal a
  failed specialist execution path and restore generalist work in the parent.
