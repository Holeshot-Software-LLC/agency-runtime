---
title: "Preserve content-free Codex child tool outcomes"
status: accepted
category: decisions
created: 2026-08-02
updated: 2026-08-02
tags: [codex, delegation, diagnostics, evidence, privacy]
related:
  - docs/roadmap/issue-AR-223-prove-codex-child-task-execution.md
  - docs/roadmap/handoffs/issue-AR-207.md
  - docs/decisions/0116-bind-product-trials-to-exact-workspace-proof.md
  - agency_runtime/core/canary_backends.py
  - agency_runtime/core/canary_proof.py
  - agency_runtime/core/evals/decision_conformance.py
  - tests/test_codex_activation_canary.py
  - tests/test_product_host.py
  - docs/worklog/README.md
supersedes: []
superseded_by: null
id: ADR-0146
type: decision
deciders: [maintainers]
---

# ADR-0146: Preserve content-free Codex child tool outcomes

## Context

Consumed writer trial `ar223-agency-writer-4c57507-01` retained one aggregate
child tool-call count but no child transcript. The authoritative Store proves
launch, activation consumption, and execution dispatch; it retains no worker
end, exit code, stdout, stderr, or tool receipt. The surviving parent rollouts
do not contain the child identity, and the isolated profile was removed after
the trial. The one historical call therefore cannot be classified honestly.

The next immutable trial must distinguish an absent tool output, a completed or
failed call, and a successful, failed, or missing patch receipt without copying
task text, arguments, paths, file content, output, or error details into the
product report.

## Decision

1. Codex product collaboration evidence uses schema v2 and preserves one fixed
   child tool-evidence projection for each exact child plus a checked aggregate.
2. The projection retains counts only: function versus custom calls; the fixed
   safe tool classes `exec`, `apply_patch`, `shell_command`, and `other`; call
   completion status; output-receipt presence; and patch success, failure, or
   unknown outcome.
3. Arbitrary tool names collapse to `other`. Arguments, paths, file changes,
   stdout, stderr, outputs, errors, task text, and response content are never
   retained in this projection.
4. Per-child counters must be internally consistent and must sum exactly to the
   aggregate. Malformed or mismatched projections cannot be published as
   product collaboration evidence.
5. These counters are diagnostic evidence only. They do not relax the existing
   requirement for a successful workspace-local patch receipt and exact file
   bytes before a writer trial can pass.

Implementation `3cc852f` carries this decision; ledger `c09e0c1` records its
worklog and roadmap traceability.

## Consequences

- A fresh one-child writer trial can identify the first missing lifecycle
  boundary without exposing private tool content.
- Multi-unit reports preserve the same evidence per child, so a writer's
  receipt cannot be hidden by an aggregate from unrelated specialists.
- The consumed `4c57507` trial remains historically unclassifiable; v2 evidence
  is not manufactured retroactively.
- A focused decision mutation proves that dropping successful patch receipts is
  detected by the fixed projection test.

## Alternatives

- **Retain full child tool events.** Rejected because task arguments, paths,
  output, file content, and errors exceed the product report's privacy boundary.
- **Keep only the existing total call count.** Rejected because one call does
  not distinguish dispatch, output, wrapper completion, or patch outcome.
- **Rerun the consumed candidate.** Rejected because immutable trials are
  one-shot evidence and rerunning would erase the causal boundary.
