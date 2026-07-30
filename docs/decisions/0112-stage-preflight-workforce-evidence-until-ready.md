---
title: "Stage preflight workforce evidence until ready"
status: accepted
category: decisions
created: 2026-07-28
updated: 2026-07-29
tags: [routing, workforce, evidence, transactions, preflight]
related:
  - docs/roadmap/issue-AR-199-restore-codex-workforce-evidence.md
  - docs/roadmap/issue-AR-200-diagnosable-decision-conformance.md
  - docs/decisions/0003-response-telemetry-is-model-truth.md
  - docs/decisions/0081-compile-contractors-from-governed-structured-contracts.md
  - docs/decisions/0093-atomic-finalization-evidence-batches.md
supersedes: []
superseded_by: null
id: ADR-0112
type: decision
deciders: [maintainers]
---

# ADR-0112: Stage preflight workforce evidence until ready

## Context

Native preflight must make provider-backed workforce selection and governed
contractor hiring available before it can build the specialist context and
delegation plan. It must also leave no routing, receipt, hiring-case, roster, or
prompt-version state behind when its lease expires or its ready-state
compare-and-swap loses.

Routing with no Store preserved atomicity but disabled model receipts and
hiring. Routing with the unrestricted live Store would make those features
available while permitting durable writes before the ready decision.

## Decision

Native preflight gives routing the governed Store for read-only workforce and
hiring checks, while suppressing ordinary routing and receipt writes. Provider
attempts and validated contractor changes are projected into bounded pending
evidence. A validated pending contractor may participate in in-memory staffing,
prompt hydration, and assignment construction, but it is not durable state.

`mark_preflight_ready` validates the pending evidence and commits provider
receipts, hiring cases, immutable prompt versions, workers, and routing evidence
inside the same `BEGIN IMMEDIATE` transaction that wins the ready-state CAS.
CAS loss, validation failure, daily-limit change, or any governed Store failure
rolls the transaction back. Replaying an already-ready preflight does not repeat
the writes.

Only the package-owned Codex activation canary may recover its exact constant
goal from the current opaque persisted spawn-message form. The host, parent
scope, task label, and persisted assignment must already correlate, and normal
native-child goals retain exact equality.

## Consequences

- Workforce inference and same-task contractor hiring are available during
  native preflight without partial durable state.
- Current-turn model receipts become authoritative only when the turn becomes
  ready.
- Pending specialists require a narrow read-only hydration view before commit.
- Daily hiring limits are checked once during planning and again while the
  serialized ready transaction owns the write boundary.
- The canary accommodates Codex's opaque rollout representation without
  weakening ordinary child-goal enforcement.

## Alternatives

- **Keep routing Store-free.** Rejected because configured inference can run but
  cannot persist receipts or hire a proven gap.
- **Pass the unrestricted Store and accept early writes.** Rejected because a
  failed or losing preflight would leave evidence and workforce mutations that
  never belonged to a ready turn.
- **Repair only the rendered header.** Rejected because it would conceal missing
  specialist and model evidence rather than restore it.
- **Accept opaque goal messages for every native child.** Rejected because it
  would weaken the exact persisted-goal boundary.
