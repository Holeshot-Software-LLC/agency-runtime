---
title: "AR-140: Scale routing, retrieval, and CLI startup"
status: open
category: roadmap
created: 2026-07-26
updated: 2026-07-26
tags: [performance, routing, retrieval, cli, benchmarks]
related:
  - docs/roadmap/issue-AR-11-routing-evaluation-and-performance.md
  - docs/decisions/0030-versioned-quantitative-evaluation-gates.md
  - agency_runtime/core/selector/semantic_retrieval.py
  - agency_runtime/core/preflight.py
supersedes: []
superseded_by: null
type: issue
epic: performance
issue_id: AR-140
priority: p1
tracker_url: null
depends_on: []
blocks: []
---

# AR-140: Scale routing, retrieval, and CLI startup

## Problem

The isolated cached-routing p95 gate exceeds 2 ms in every current sample.
Semantic retrieval scales to seconds and hundreds of MiB at 10,000 agents, and
CLI startup is roughly 840 ms. Full-route warm latency remains tens of
milliseconds even when the narrow microbenchmark is fast.

## Current state

Initial cached p95 samples were 2.193-3.579 ms; uncached correctness and the
20 ms ceiling passed. A first optimization restored isolated results but an
integrated arm later measured 2.103 ms, proving that its margin was not
sufficient. Semantic retrieval was about 6-7.4 seconds cold and 199-414 ms
warm at 10,000 agents with roughly 208 MiB peak memory. These are local
benchmark observations, not cross-platform release evidence.
Deeper profiling found a separate stable-state cost: the operational routing
snapshot took 1,104.677 ms, including a 233.371 ms full-roster fallback
presence check, while `python -m agency_runtime.cli --version` imported the
heavy compatibility facade and took about 647 ms.

## Approach

Profile before changing controls; reuse coherent route requests, compute query
vectors once, cache immutable feature indexes by exact roster revision, batch
Store reads, and defer heavy CLI imports. Add size-tiered memory and latency
gates that preserve routing correctness and existing cold/one-call controls.
For stable startup, query only the two governed fallback identities through the
complete active-definition join, and reuse the already captured immutable
snapshot only when a fresh trusted roster generation proves reconciliation
made no routing-visible change.

## Dependencies

AR-130 forbids unsafe trust caching. AR-133 provides safe transaction batching.

## Acceptance

- Existing routing correctness gates remain perfect.
- Cached and full-route latency gates pass on isolated supported runners.
- 263, 1,000, and 10,000-agent retrieval has explicit time and memory budgets.
- Cache keys bind exact configuration and roster revisions.
- CLI startup has a reproducible regression threshold.

## Implementation evidence

Revision-aware semantic indexes, posting-based candidate narrowing, one-query
feature reuse, and bounded caches preserve exact selection hashes. Controlled
local results were: 263 agents 316.006 ms cold / 2.031 ms warm p95 / 6.922 MiB;
1,000 agents 1,293.429 ms / 7.412 ms / 21.329 MiB; and 10,000 agents
8,817.588 ms / 84.193 ms / 189.589 MiB. The lightweight version entrypoint
measured 116.244 ms p50 and 129.574 ms p95 across seven fresh processes.
The cached-routing path removed redundant full-roster identity work, uses a
recursively detached JSON-like cache clone, and reuses an opaque eligibility
validation proof instead of repeating the same detached roster comparison in
fingerprinting. Mutation changes issue a new proof; opaque inputs fall back to
the prior conservative checks. Five unchanged 1,000-agent controls produced
deterministic median cache-hit p95 values of 1.345, 1.448, 1.318, 1.442, and
1.745 ms. The exact 12-module mixed reproducer passes 424 tests, including the
unchanged 2.0 ms contract. Correctness, compatibility, roster, semantic,
selector, and the isolated 101-test distribution/release package pass. These
are fixed local controls, not cross-platform superiority or supported-runner
evidence.

The bounded stable-state slice routes the module entrypoint through the lazy
CLI dispatcher, reducing `python -m agency_runtime.cli --version` from about
647 ms to 112 ms. The complete-definition fallback lookup is capped at 16
identities and reduced its measured check from 233.371 ms to 22.453 ms.
Generation-proven snapshot reuse reduced stable operational capture from
1,104.677 ms to 663.671 ms without a trust cache; any mutation forces a
complete recapture. The affected suites pass 104 tests. At that checkpoint,
packaged-contractor reconciliation remained the dominant 400-450 ms cost and
the 1.585-second, 276-query no-op starter reconciliation remained open; the
final bounded batch below supersedes that local cost state.

The final audit reproduced host-scheduling variance in the 10,000-agent warm
gate: one unchanged five-sample arm failed at 181.144 ms before an unchanged
rerun passed at 127.495 ms. Profiling attributed 92.6 percent of warm time to
cosine scoring: 3,750 eligible agents each walked roughly 109 dimensions even
though the query had 49. Compiled vectors are now immutable feature-addressable
maps and cosine walks the smaller vector. The exact selected-result hash remains
`9214506c8a46c50e1cff4b2e0793127935c10f8f092d5a8597c8623cf4f69f60`;
the final representation measured 7,839.770 ms cold, 53.825 ms warm p95 across
five samples, and 167.817 MiB peak. The 60-test semantic/selector/fallback suite
passes, including revision-identity mutation rejection. No gate, sample count,
trust validation, or exclusion changed.

The remaining packaged-contractor startup cost now uses one bounded,
parameterized worker snapshot for all nine canonical slugs instead of nine
separately trusted SQLite connections. A paired 21-sample warm Windows control,
alternating the legacy and batch paths against the same already-seeded Store
with schema construction and warmup excluded, reduced no-op contractor install
from 160.340 ms median / 169.247 ms p95 to 28.712 / 30.021 ms. The complete
stable operational snapshot fell from 539.410 / 552.708 ms to 408.184 /
415.685 ms. Installer opens and worker SELECTs fell from nine to one; the full
snapshot fell from 13 to five opens and 15 to seven SELECTs. Exact snapshot
key/value binding and Store uniqueness/transaction checks keep concurrent
identity conflicts fail-closed. The broad workforce, preflight, and routing
suite passes 370 tests with two skips and one expected failure. These remain
local warm controls, not hosted or cross-platform evidence.

A later production-spine profile found 74,256 repeated serializations across
only 544 immutable workforce contracts. A 512-entry least-recently-used cache
now owns the canonical bytes; the frozen, tuple-only contract remains the full
cache key, replacement creates a distinct key, and eviction is covered. The
exact exhaustive workforce-evidence hotspot fell from 5.45 to 2.66 seconds on
the measured Windows host without changing a fingerprint or selection
contract. This is a bounded same-machine result, not supported-runner evidence.
