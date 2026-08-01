---
title: "Bind opaque Codex execution by ciphertext identity"
status: accepted
category: decisions
created: 2026-08-01
updated: 2026-08-01
tags: [codex, delegation, execution, ciphertext, evidence]
related:
  - docs/roadmap/issue-AR-223-prove-codex-child-task-execution.md
  - docs/roadmap/handoffs/issue-AR-207.md
  - docs/decisions/0094-durable-native-child-correlation.md
  - docs/decisions/0128-persist-exact-codex-plan-authority-and-serialize-launches.md
  - docs/decisions/0135-require-explicit-codex-child-execution-turns.md
  - docs/decisions/0137-reconcile-codex-followup-completion-at-parent-stop.md
  - agency_runtime/core/codex_child_execution.py
  - agency_runtime/core/canary_backends.py
  - agency_runtime/core/native_child_prompt_delivery.py
  - tests/test_codex_activation_canary.py
  - tests/test_codex_child_execution.py
  - docs/worklog/README.md
supersedes:
  - docs/decisions/0135-require-explicit-codex-child-execution-turns.md
superseded_by: null
id: ADR-0136
type: decision
deciders: [maintainers]
---

# ADR-0136: Bind opaque Codex execution by ciphertext identity

## Context

ADR-0135 correctly separated a Codex child's activation turn from its later
execution turn, but assumed the receiving child's persisted rollout exposed the
decrypted execution envelope. Exact merged build `a2d1a7c` disproved that
assumption. Codex delivers the decrypted task to the child model while storing
the incoming root-to-child message as ciphertext. The same 760-character
ciphertext appears exactly once in the parent's `followup_task` call and exactly
once in the child's later turn; no hook or retained rollout exposes the
plaintext at that boundary.

The accepted activation context already binds the exact work-unit ID, native
task name, specialist identity, goal hash, child identity, and mutation scope.
The follow-up is the one-use trigger for that staged authority, not a new source
of task authority.

## Decision

For every governed Codex work unit:

1. Preserve ADR-0135's exact activation-only `spawn_agent`, first wait,
   one-use `followup_task`, and second wait sequence. The parent remains
   non-working and cannot retry, reuse, or substitute another message path.
2. The parent `PreToolUse` hook binds the opaque follow-up to the one exact
   activated child path and atomically claims its Store worker run with the
   exact follow-up tool-use ID.
3. A passed worker requires one child rollout with exact parent lineage, two
   ordered successful turns, and one current-host root-to-child `NEW_TASK`
   record in the second turn. Its ciphertext must byte-match the exact
   ciphertext in the parent's uniquely identified follow-up call. The parent
   rollout must identify its own session, tool-use ID, and canonical child
   target. Same-day and immediately prior-day transcript locations are the only
   accepted parent search scope.
4. The projected execution identity comes only from the already verified
   activation delivery's work-unit ID and goal hash plus its canonical native
   task name. Ciphertext is compared transiently and is never copied into
   Store, reports, headers, diagnostics, or public evidence. Plaintext-capable
   fixtures and future compatible hosts must still carry one exact canonical
   execution envelope.
5. Missing, duplicate, mismatched, cross-child, cross-parent, malformed,
   link-unsafe, wrong-turn, or unbounded evidence fails closed. Activation and
   product proofs both use this same boundary.

## Implementation evidence

Commit `65ee298` implements the ciphertext-identity boundary and merge commit
`5ff4a08` publishes it through [PR 231](https://github.com/Holeshot-Software-LLC/agency-runtime/pull/231).
The committed tree passes 72 focused tests, the named Python spine with 656
passes and 6 skips, 110 dashboard tests, 627-document validation, repo-wide
Ruff lint and format, every routing threshold, and all 86 decision mutations
with zero survivors or invalid results and unchanged source.

## Consequences

- Agency can prove that the exact host message authorized by the parent hook is
  the exact message that caused the activated child's second turn without
  claiming access to plaintext the host does not retain.
- The first readiness turn still cannot pass a worker, and Store's one-use
  dispatch claim remains mandatory before any lifecycle boundary closes it.
  ADR-0137 defines exact parent-`Stop` reconciliation for current Codex, which
  does not emit a second `SubagentStop` after `followup_task`.
- No new database column or sensitive message digest is required. Exact
  ciphertext exists only during bounded local comparison.
- Cross-midnight child launches remain supported through the immediately prior
  rollout day without broad recursive transcript search.

## Alternatives

- **Require decrypted child rollout text.** Rejected because current Codex does
  not persist it; exact live evidence disproved the premise.
- **Trust the second completion alone.** Rejected because it would not bind the
  turn to the parent call, Store dispatch, child path, or staged goal.
- **Persist ciphertext or its digest in Store.** Rejected because exact bounded
  parent and child rollouts already support transient comparison, so new
  durable sensitive state and a schema migration add no proof.
- **Rerun or reinterpret the failed activation.** Rejected because governed
  attempts are immutable; the consumed failure remains terminal evidence.
