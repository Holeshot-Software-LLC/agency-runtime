---
title: Treat response telemetry as model truth
status: accepted
category: decisions
created: 2026-07-10
updated: 2026-07-10
tags: [observability, models, receipts]
related: []
supersedes: [docs/decisions/0002-model-attribution-from-post-request-logs.md]
superseded_by: null
id: ADR-0003
type: decision
deciders: []
---

# ADR-0003: Treat response telemetry as model truth

## Context

Requested aliases can route dynamically, while retrospective logs are delayed and difficult to correlate safely. The host response is closest to the request and can expose the resolved provider and model without a second lookup.

## Decision

Build model receipts from request-time host or provider response telemetry. Store the requested alias separately from the resolved provider and model. If the host emits no authoritative model data, record resolved_model as unavailable rather than infer or invent a value.

All adapters normalize receipts into the same store contract. The observability header may show a complexity tier for the requested model group, but that tier does not replace the resolved-model evidence.

## Consequences

- Receipts describe what the host actually reported for the request.
- Dynamic routing and fallback remain observable.
- Hosts with weaker telemetry produce honest unavailable records.
- Each host integration must pass response metadata and session identity correctly.

## Alternatives

- Continue querying post-request logs. Rejected by ADR-0002 because races and stale matches can produce false claims.
- Treat the requested alias as the actual model. Rejected because routing aliases deliberately hide the resolved deployment.
- Omit receipts on telemetry-poor hosts. Rejected because an explicit unavailable receipt is auditable and distinguishes missing evidence from missing instrumentation.

## Provenance

Commit cfc7d38 established response-body model capture. Commits 8b377b1 and 2235d7e applied the normalized, honest-receipt behavior across the shared adapter surface.
