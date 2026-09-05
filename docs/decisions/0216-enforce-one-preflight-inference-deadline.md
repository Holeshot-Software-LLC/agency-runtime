---
title: "Enforce one preflight inference deadline"
status: accepted
category: decisions
created: 2026-09-05
updated: 2026-09-05
tags: [staffing, reliability]
related:
  - docs/roadmap/issue-AR-401-enforce-preflight-deadlines-at-provider-boundaries.md
  - docs/decisions/0214-close-a-preflight-attempt-on-its-token-not-its-lease.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
id: ADR-0216
type: decision
deciders: [owner]
---

# ADR-0216: Enforce one preflight inference deadline

## Context

AR-398's admission estimate does not bound calls within a round. Three valid
50-second responses overran a simulated 75-second lease. Planning, recall,
repairs and fallback also consume the same host-process lease.

## Decision

Bind the route-request lease to one request-local absolute monotonic inference
cutoff, ten seconds before expiry. Nested work cannot extend it. Every structured
and hiring stage checks before each call, clamps its timeout, and rejects late
responses. Structured HTTP, embeddings and native reranking bound response reads
against that same cutoff. Reset context on every exit. Direct calls without a
preflight deadline retain their configured timeout; direct hiring may receive an
explicit cutoff.

Keep the round estimate as an admission heuristic, not enforcement. Name
provider_deadline_exhausted or hiring_lease_budget_exhausted; do not commit an
incomplete pending hire. Keep the token-guarded failure close and lease-guarded
ready commit. Do not renew the main lease.

## Consequences

Sequential stages cannot each spend the original full timeout. The reserved
terminal interval is a budget, not an OS scheduling guarantee; non-provider
setup remains separately measurable. Future background threads must explicitly
propagate the request context. Clock tests are not live-canary evidence.

## Alternatives

A worst-case round estimate starves fast hiring. Increasing host timeouts merely
delays failure. Disabling critics changes quality and does not enforce a deadline.
