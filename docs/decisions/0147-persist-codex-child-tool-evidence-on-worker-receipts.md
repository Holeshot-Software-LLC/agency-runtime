---
title: "Persist Codex child tool evidence on worker receipts"
status: accepted
category: decisions
created: 2026-08-02
updated: 2026-08-02
tags: [codex, delegation, diagnostics, evidence, privacy, store]
related:
  - docs/roadmap/issue-AR-223-prove-codex-child-task-execution.md
  - docs/roadmap/handoffs/issue-AR-207.md
  - docs/decisions/0146-preserve-content-free-codex-child-tool-outcomes.md
  - agency_runtime/core/codex_child_tool_evidence.py
  - agency_runtime/core/evals/product_host.py
  - agency_runtime/core/store/native_child.py
  - agency_runtime/core/store/evidence.py
  - agency_runtime/core/canary_proof.py
  - agency_runtime/core/evals/decision_conformance.py
  - tests/test_native_child_lifecycle.py
  - tests/test_product_host.py
  - tests/test_codex_activation_canary.py
  - tests/test_schema_v36_invariants.py
  - docs/worklog/README.md
supersedes: []
superseded_by: null
id: ADR-0147
type: decision
deciders: [maintainers]
---

# ADR-0147: Persist Codex child tool evidence on worker receipts

## Context

ADR-0146 preserves a fixed, content-free child tool summary in the product
collaboration report. That report is assembled after the host process exits.
The canonical SQLite Store still retains only the worker lifecycle, activation,
and dispatch receipts, so an interrupted report path or later diagnosis cannot
independently recover the child tool boundary.

Product admission must not depend on a transient projection that the Store
cannot corroborate. It also must not copy prompts, arguments, paths, output,
errors, task text, or response content into durable state.

## Decision

1. Schema v44 adds one optional tool-evidence projection to each existing
   `worker_runs` receipt: schema, canonical fixed-count JSON, source, and
   recorded timestamp. No separate uncorrelated event table is introduced.
2. Only the ADR-0146 count fields are accepted. Counts are bounded and
   internally reconciled before serialization; all other keys fail before a
   Store write.
3. The first exact Codex child receipt write is immutable. A byte-identical
   replay is idempotent, while a different projection or a missing exact
   session, trace, work-unit, child, backend, or native-run identity fails.
4. The product host writes each validated rollout projection before reading the
   exact activation snapshot. Product proof requires the Store projection to
   equal the corresponding rollout child projection.
5. Activation snapshots expose `recorded`, `missing`, or `invalid` status per
   worker. A missing, corrupt, or failed Store write remains a fixed,
   unit-scoped product failure instead of becoming an opaque reconciliation
   exception.

## Consequences

- The next immutable writer sentinel can be diagnosed from canonical Store
  state even if report generation is interrupted.
- A report cannot claim child tool evidence that was not durably attached to
  the same exact worker receipt.
- Historical workers remain valid with `missing` evidence; no prior trial is
  reinterpreted or backfilled.
- Schema migration is additive and idempotent. Corrupt partial projections are
  visible as `invalid` and cannot pass product admission.
- A curated mutation removes the product-host Store write and must be killed by
  the exact product-host test.

Implementation `2a19c79` carries this decision; ledger `e0a7492` records its
worklog and roadmap traceability.

## Alternatives

- **Keep the report as the only copy.** Rejected because diagnosis would still
  depend on one transient post-process projection.
- **Persist full child tool events.** Rejected because those events can contain
  private prompts, arguments, paths, output, errors, and task content.
- **Create a free-standing telemetry table.** Rejected because the existing
  exact worker receipt already owns the child identity and lifecycle boundary.
