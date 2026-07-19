---
title: "Derive runtime claims from authoritative correlated evidence"
status: accepted
category: decisions
created: 2026-07-10
updated: 2026-07-16
tags: [evidence, tracing, delegation]
related:
  - docs/roadmap/issue-AR-45-bind-store-privacy-to-explicit-config.md
  - docs/roadmap/issue-AR-10-authoritative-runtime-evidence.md
  - docs/roadmap/issue-AR-12-installed-operations-dashboard.md
  - docs/roadmap/issue-AR-24-deterministic-evidence-ordering.md
  - docs/roadmap/issue-AR-25-turn-scoped-specialist-evidence.md
  - docs/roadmap/issue-AR-27-authoritative-delegation-stop-enforcement.md
  - docs/roadmap/issue-AR-33-openclaw-final-outbound-seal.md
  - docs/roadmap/issue-AR-69-require-correlation-complete-cli-delegation-evidence.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
id: ADR-0027
type: decision
deciders: []
---

# ADR-0027: Derive runtime claims from authoritative correlated evidence

## Context

A tool name, model-authored header, selected agent, or started worker is not
proof that an operation completed. Earlier behavior could promote failed tool
results, correlate a delegation to the first open suggestion rather than the
intended work unit, continue dependent work after failure, or accept a response
claim that disagreed with the canonical store.

Routing also needs a durable per-request identity. Cached selection data may be
reused, but a new request must not inherit the previous request's evidence
identity.

## Decision

Treat the SQLite evidence store as the authority for externally visible runtime
claims. Every request receives a unique trace and routing-decision identity.
The persisted decision stores a bounded query hash, routing fingerprint,
selection source and status, selected IDs, provider information, and work-unit
metadata; it does not require the raw prompt.

Promote load, delegation, worker, and model evidence only when the observed
result satisfies the corresponding success contract. Correlate delegation by a
stable work-unit identity plus session/trace context. Reject duplicate work-unit
IDs, fail missing results explicitly, and skip dependents when a prerequisite
does not complete successfully. Merge only successful predecessor work.

Final response fields are derived from or reconciled with canonical events.
Model-authored values that are absent, stale, ambiguous, spoofed, or
contradictory do not override stored truth. Cache hits may reuse selection
content, but finalization assigns a fresh trace before persistence.

## Consequences

- Evidence consumers can follow one request through routing, delegation, model
  receipts, and finalization without relying on display text.
- Failed operations remain visible as failed or skipped instead of disappearing
  or becoming success.
- Host adapters must preserve session, trace, turn, tool-call, and work-unit
  correlation fields across their native payloads.
- Legacy rows require migration or explicit evidence-only parents so foreign-key
  and uniqueness constraints remain valid.
- A missing host signal produces an honest unknown/unavailable state, which can
  make the UI less optimistic but more trustworthy.

## Alternatives

- Trust the response header. Rejected because the model can invent or copy a
  plausible claim without executing anything.
- Treat every tool invocation as success. Rejected because failure and timeout
  results are part of normal host behavior.
- Reuse the cached trace with the cached selection. Rejected because it merges
  separate requests into one audit identity.
- Correlate only by agent name. Rejected because multiple independent work units
  can use the same specialist.

## Provenance

The production-readiness refactor added failure-aware event promotion, stable
work-unit correlation, dependency gating, canonical header reconciliation,
spoof rejection, unique traces, and persisted routing-decision records. The
implementation commit is recorded through the worklog after it is created.
