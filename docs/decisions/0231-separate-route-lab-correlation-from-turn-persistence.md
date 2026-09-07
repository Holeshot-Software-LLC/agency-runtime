---
title: "Separate Route Lab correlation from durable turn evidence"
status: superseded
category: decisions
created: 2026-09-07
updated: 2026-09-07
tags: [dashboard, diagnostics, correlation, acceptance]
related:
  - docs/decisions/0232-represent-route-lab-observations-by-trace-digest.md
  - docs/roadmap/issue-AR-173-correlate-route-lab-observations.md
  - docs/decisions/0027-authoritative-runtime-evidence-traces.md
  - docs/decisions/0053-durable-fail-enabled-master-control.md
  - docs/decisions/0105-bound-delivery-to-live-demo-checkpoints.md
  - agency_runtime/core/selector/explain.py
  - agency_runtime/core/observability.py
  - docs/worklog/README.md
supersedes: []
superseded_by: docs/decisions/0232-represent-route-lab-observations-by-trace-digest.md
id: ADR-0231
type: decision
deciders: [maintainers]
---

# ADR-0231: Separate Route Lab correlation from durable turn evidence

## Context

AR-173 usefully requires Route Lab response/HTTP observation identity equality,
but its narrative incorrectly promises persisted routing evidence. Diagnostic
explanations already explicitly excluded durable turn evidence at e5f4a8c2,
before AR-173 was written. The original server regression is no longer present.
Logging emits a bounded observation envelope; it is not a SQLite routing row.

The phrase every request also needs the existing disabled/invalid-request
boundary: ADR-0053 forbids inventing a routing trace for a bypass. A content-free
HTTP request ID and a routing trace are different identities.

## Decision

Reconcile AR-173 before isolated acceptance, preserving original wording:

- Criterion 1 applies to admitted, enabled Route Lab routing operations. Allocate
  one fresh UUIDv4 and attach it to the current observation before explain_route.
  Invalid or disabled requests do not create synthetic routing traces.
- Criterion 4 requires a real authenticated HTTP regression that joins the
  response trace to the exact emitted request log envelope by its domain-
  separated digest, and verifies no diagnostic turn/routing rows are created.
- Criterion 5 uses ADR-0105's focused checks and named production spine instead
  of a mandatory exhaustive release gate. Criteria 2 and 3 are unchanged.

Keep emitted content-free operational logging separate from durable turn
evidence. This does not add log persistence, retention guarantees, turn writes,
credentials or host authority. Actual preflight still owns durable lifecycle
evidence; no production behavior is changed by this reconciliation.

## Consequences

Two real loopback requests can prove fresh per-operation identity, attachment
before explanation, response-to-log equality and content-free bounded fields
without paying for model inference. A disabled response remains an honest
bypass, not a fabricated routing receipt. The log is captured in the regression;
this does not claim host logging configuration durably retained it on disk.

## Alternatives

- Persist diagnostic routing as real turns: creates misleading evidence and
  contradicts the existing explain_route lifecycle boundary.
- Allocate traces for disabled calls: contradicts ADR-0053's bypass contract.
- Treat a UUID-shaped response alone as correlation proof: misses mismatched
  or unbound request observations.
- Silently rewrite the record or retire the useful identity requirement:
  discards the defect's remaining relevant regression contract.
