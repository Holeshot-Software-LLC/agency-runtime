---
title: Resolve models from post-request logs
status: superseded
category: decisions
created: 2026-07-10
updated: 2026-07-10
tags: [observability, models, historical]
related: []
supersedes: []
superseded_by: docs/decisions/0003-response-telemetry-is-model-truth.md
id: ADR-0002
type: decision
deciders: []
---

# ADR-0002: Resolve models from post-request logs

## Context

The runtime initially needed to turn a requested model alias into the deployment that actually handled a call. Persisted provider spend logs appeared to offer a common source even when the host hook exposed little response metadata.

## Decision

Correlate a completed request with recent provider log entries, using model group and time bounds. If tight time bounds miss because log persistence is delayed, retry without time bounds.

## Consequences

- Model attribution could be added without changing the request path.
- Log commit lag created a race with response finalization.
- Resolved deployments could be stored under a different group than the requested alias.
- An unbounded retry could select stale data from another request or session.

These failure modes made the result unsuitable as model truth.

## Alternatives

- Read the resolved model directly from request-time response telemetry. This became ADR-0003.
- Record only the requested alias. Rejected because an alias is not evidence of what ran.
- Leave the field empty. Safer than a false claim, but less useful when authoritative telemetry exists.

## Provenance

Commit 5eb4de1 added a no-time-bounds fallback to address the log race. Commit cfc7d38 documented why that correlation remained unreliable and replaced it.
