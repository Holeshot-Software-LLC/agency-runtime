---
title: "Cache only roster vectors across hook processes"
status: accepted
category: decisions
created: 2026-09-05
updated: 2026-09-05
tags: [performance, workforce, privacy]
related:
  - docs/roadmap/issue-AR-403-reuse-roster-embeddings-across-hook-processes.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
id: ADR-0218
type: decision
deciders: [owner]
---

# ADR-0218: Cache only roster vectors across hook processes

## Context

The native preflight is short-lived, so a process-local cache repeatedly loses
unchanged roster embeddings. Extending the lease addresses neither the repeated
work nor quality. User queries and staffing decisions are not invariant inputs.

## Decision

Keep the two-entry memory cache and add two fixed disk slots under the explicit
Store parent's private recall-vectors-v1 directory. Use existing private-path,
bounded-read and atomic-write primitives. Refuse linked, shared or unsafe paths;
cache faults are misses, not staffing failures. Concurrent atomic writers may
lose a cache entry but cannot expose partial data or affect staffing authority.

Store only positive roster document vectors in lossless little-endian float64
encoding with bounded JSON metadata, never prompts, query vectors, plans,
nominations or decisions. Bound each slot to 24 MiB and two million scalar
values. Bind the key to scope, projection, roster generation/fingerprints,
provider endpoint/model/dimensions and normalization identity. Revalidate finite
unit-normalized rows on read without changing their values. Expire both layers
after one hour, and compare each fresh query's returned actual model and
dimensions before using cached document vectors. Invalidate mismatches.

Keep all recruitment, strict critic, safety and hiring reviews. Preserve bounded
recall input-count, provider-call-count and cache-hit evidence in failure receipts.

## Consequences

Implementation: `e9d8ecea`; benchmark: `af366dd8`, indexed in the worklog registry.

A warm fresh process still calls the embedding provider for each current unit.
Cold starts, profile/roster changes and hourly expiry still pay full catalog
cost. Silent weight changes behind an unchanged model identity are undetectable;
the one-hour TTL bounds that existing provider-identity limitation. This cache
does not claim to accelerate planner, recruiter or hiring inference.
Native preflight uses the explicit Store even while durable writes are deferred;
the cache is disposable derived state, never a pending-hire commit.

## Alternatives

Persisting whole staffing decisions risks stale intent or authority. Skipping
strict review trades quality for speed. Parallelizing hiring changes call-budget
and commit semantics. Float32 quantization can perturb ties. A daemon introduces
a new lifecycle. Reuse the invariant inputs first and measure the remaining cost.
