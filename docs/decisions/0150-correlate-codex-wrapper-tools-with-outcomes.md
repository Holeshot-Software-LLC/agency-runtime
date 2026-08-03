---
title: "Correlate Codex wrapper tools with outcomes"
status: accepted
category: decisions
created: 2026-08-02
updated: 2026-08-02
tags: [codex, delegation, diagnostics, evidence, privacy, store]
related:
  - docs/roadmap/issue-AR-223-prove-codex-child-task-execution.md
  - docs/roadmap/handoffs/issue-AR-207.md
  - docs/decisions/0146-preserve-content-free-codex-child-tool-outcomes.md
  - docs/decisions/0148-classify-nested-codex-exec-tools-without-content.md
  - docs/decisions/0149-classify-codex-wrapper-failures-without-content.md
  - agency_runtime/core/codex_child_tool_evidence.py
  - agency_runtime/core/canary_backends.py
  - agency_runtime/core/evals/decision_conformance.py
  - tests/test_codex_activation_canary.py
  - tests/test_native_child_lifecycle.py
  - tests/test_product_host.py
  - docs/worklog/README.md
supersedes: []
superseded_by: null
id: ADR-0150
type: decision
deciders: [maintainers]
---

# ADR-0150: Correlate Codex wrapper tools with outcomes

## Context

Store v3 records nested tool kinds, wrapper outcomes, and failure categories as
separate aggregates. Consumed writer trial `ar223-agency-writer-6e0d3c6-01`
contains one patch wrapper and two shell wrappers, with one completion and two
residual process failures. Those aggregates cannot prove whether the patch or
a shell wrapper completed, so they cannot identify the first failed boundary
without another speculative trial.

## Decision

1. Child tool evidence v4 retains every v1 through v3 field and adds a fixed
   matrix for `apply_patch`, `shell_command`, `other`, and `ambiguous` against
   `completed`, `failed`, `yielded`, and `unknown` wrapper outcomes.
2. A wrapper receives a concrete tool kind only when its bounded input contains
   exactly one directly classified nested tool call. Empty, multiple, dynamic,
   malformed, duplicate, or otherwise uncertain wrappers are `ambiguous`.
3. The projector retains call identifiers and classifications only transiently.
   Store persists integer counts and never commands, paths, prompts, output, or
   errors.
4. For each outcome, the four tool-kind counts must sum exactly to its existing
   aggregate wrapper count. New Store rows use canonical v4; canonical v1,
   v2, and v3 rows remain readable without reinterpretation.
5. A curated mutation collapses the concrete tool kind to `ambiguous` and must
   be killed by the fixed product projector test.

## Consequences

- A future immutable writer trial can distinguish patch failure from shell
  failure using its worker receipt alone.
- The matrix is diagnostic evidence, not proof that a tool changed the
  workspace or that the delegated unit completed.
- Multi-tool wrappers remain visible but intentionally ambiguous rather than
  receiving a misleading nearest classification.

## Alternatives

- **Persist raw wrapper inputs or outputs.** Rejected because they may contain
  private task material, commands, paths, and repository content.
- **Pair only patch counts with failures.** Rejected because shell and future
  allowlisted tool wrappers would remain indistinguishable.
- **Assign a dominant tool to multi-tool wrappers.** Rejected because ordering
  and causality are not proven by static occurrence counts.
- **Rerun the v3 build.** Rejected because the consumed trial is immutable and
  repeating it would not repair the evidence contract.
