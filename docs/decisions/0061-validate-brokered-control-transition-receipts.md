---
title: "Validate brokered control transition receipts against deterministic CAS semantics"
status: superseded
category: decisions
created: 2026-07-16
updated: 2026-07-26
tags: [security, operations, evidence, concurrency, dashboard]
related:
  - docs/roadmap/issue-AR-77-validate-brokered-control-transition-receipts.md
  - docs/decisions/0053-durable-fail-enabled-master-control.md
  - docs/decisions/0057-generation-checked-host-control-mutations.md
  - docs/decisions/0058-broker-restricted-windows-host-controls.md
  - docs/decisions/0090-model-facing-control-paths-are-read-only.md
  - docs/roadmap/issue-AR-128-seal-model-facing-control-authority.md
  - docs/THREAT_MODEL.md
  - docs/worklog/README.md
supersedes: []
superseded_by: docs/decisions/0090-model-facing-control-paths-are-read-only.md
id: ADR-0061
type: decision
deciders: [maintainers]
---

# ADR-0061: Validate brokered control transition receipts against deterministic CAS semantics

## Context

Authentication proves which local service answered, not that a response matches
the requested transition. The Store contract already defines deterministic
generation behavior, so accepting only schema-valid broker output is weaker than
the direct path.

## Decision

Bind each broker mutation to the state and generation observed immediately
before it. If the requested state already holds, generation must remain equal.
If state changes, generation must increase by exactly one. Require the response's
success flag, changed truth, requested state, top-level generation, and nested
status to agree. For Store-backed host control, also require the response's
config path/revision, environment-override identity, active and desired Store
paths, and false restart-required state to match the immediately preceding
snapshot and the restricted client's default identity. Reject an
effective-enabled host when either master or host control is false. Overflow,
stale state, missing fields, opposite state, Store drift, and generation jumps
are terminal and never retried automatically.

## Consequences

- Brokered and direct controls now have the same evidence strength.
- A stale or defective service cannot turn an invalid receipt into CLI success.
- An authenticated service bound to stale SQLite state cannot satisfy a current
  config-bound control request.
- Operators must refresh and retry explicitly after a real conflict.

## Alternatives

- Trust every authenticated response. Rejected because authentication is not a
  postcondition proof.
- Accept any increasing generation. Rejected because skipped generations hide
  races or unrelated transitions.
- Retry automatically. Rejected because it can overwrite a concurrent choice.

## Provenance

`AR-77` records implementation and verification; commit provenance is added
after the substantive commit exists.
