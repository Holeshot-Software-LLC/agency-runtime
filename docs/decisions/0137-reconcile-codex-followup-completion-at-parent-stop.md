---
title: "Reconcile Codex follow-up completion at parent Stop"
status: accepted
category: decisions
created: 2026-08-01
updated: 2026-08-01
tags: [codex, delegation, lifecycle, completion, evidence]
related:
  - docs/roadmap/issue-AR-223-prove-codex-child-task-execution.md
  - docs/roadmap/handoffs/issue-AR-207.md
  - docs/decisions/0094-durable-native-child-correlation.md
  - docs/decisions/0128-persist-exact-codex-plan-authority-and-serialize-launches.md
  - docs/decisions/0135-require-explicit-codex-child-execution-turns.md
  - docs/decisions/0136-bind-opaque-codex-execution-by-ciphertext-identity.md
  - agency_runtime/adapters/hooks.py
  - agency_runtime/core/codex_child_execution.py
  - tests/test_codex_activation_canary.py
  - tests/test_codex_child_execution.py
  - docs/worklog/README.md
supersedes: []
superseded_by: null
id: ADR-0137
type: decision
deciders: [maintainers]
---

# ADR-0137: Reconcile Codex follow-up completion at parent Stop

## Context

ADR-0136 proves that one exact parent `followup_task` ciphertext caused the
activated child's second execution turn. Exact build `5ff4a08` then exposed a
separate lifecycle mismatch: current Codex emits `SubagentStop` after the
activation-only first turn but does not emit another `SubagentStop` after a
later `followup_task` turn. The child transcript nevertheless contains the
second `task_started`, exact execution input, nonempty assistant final response,
and matching `task_complete`. The parent reaches its documented `Stop` hook
with the authoritative parent transcript path after those facts are durable.

The previous fixtures fabricated a second `SubagentStop`, so they could pass
while the real Store worker remained open with `ended_at = null`. Treating that
missing callback as an inference, routing, or trust failure would misdiagnose a
host lifecycle contract mismatch.

## Decision

1. Preserve the activation-only `SubagentStop` as a non-terminal receipt. It
   cannot close a planned worker or manufacture execution evidence.
2. At the parent Codex `Stop`, resolve only the exact active Store candidates
   for the current session and trace. Each candidate must already carry its
   one-use execution tool-use claim.
3. Use the exact parent `transcript_path` to resolve one child rollout by the
   claimed worker ID on the same day or immediately following day. The child
   must resolve back to that exact parent transcript and preserve the canonical
   parent session and native task lineage.
4. Close the worker successfully only when the bounded transcripts prove two
   ordered child turns, byte-equal parent and child execution ciphertext, the
   execution input before the response, exactly one nonempty turn-bound
   assistant `final_answer`, and a matching terminal `task_complete` message.
5. Record the terminal worker outcome directly through the atomic Store end
   transition before final response verification. Missing, duplicate,
   reordered, malformed, linked, cross-parent, cross-child, or ambiguous
   evidence causes no lifecycle mutation and remains a visible verification
   failure.
6. Compare execution and response content only transiently. Do not persist
   ciphertext, response text, hashes derived from either, or transcript paths
   in Agency evidence.

## Consequences

- The real Codex lifecycle can close an executed specialist without relying on
  a callback the host does not emit.
- Parent `Stop` does not trust the parent model's claim or a generic child
  completion. It reconciles the same Store dispatch, parent call, child
  lineage, causal input, final response, and terminal turn already required by
  the activation proof.
- A crash cannot strand an outcome-free stop between separate Store writes;
  the reconciler uses the atomic terminal child transition directly.
- Transcript parsing remains a current-host adapter concern. The projector is
  bounded, link-resistant, fail-closed, and covered by exact host-shape tests
  because Codex documents that transcript format as unstable.

## Implementation evidence

Commit `62ea12a` implements the parent-`Stop` reconciler and its causal
projector. The exact consumed `5ff4a08` parent and child rollouts reproject as
`completion_observed=True` without mutating their terminal failed evidence.
Forty-four focused tests pass after two review passes. The named local gate
passes 656 Python tests with 6 skips, 110 dashboard tests, 628-document
validation, repo-wide Ruff lint and format, every routing threshold, and 90 of
90 killed decision mutations with zero survivors or invalid results and
unchanged source.

## Alternatives

- **Wait for a second `SubagentStop`.** Rejected because two immutable live
  trials prove current Codex does not emit it after `followup_task`.
- **Keep fabricating the callback in tests.** Rejected because it tests an
  impossible host sequence and conceals the open worker.
- **Close from the second wait result.** Rejected because current wait output
  does not identify the worker or prove the child's causal response, and its
  post-tool hook may run before the full transcript is durable.
- **Treat any second `task_complete` as success.** Rejected because completion
  alone does not bind the parent dispatch, exact execution input, response
  ordering, child lineage, or final answer.
