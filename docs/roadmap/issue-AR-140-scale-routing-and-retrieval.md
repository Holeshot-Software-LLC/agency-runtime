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

Measured cached p95 samples were 2.193-3.579 ms; uncached correctness and the
20 ms ceiling passed. Semantic retrieval was about 6-7.4 seconds cold and
199-414 ms warm at 10,000 agents with roughly 208 MiB peak memory. These are
local benchmark observations, not cross-platform release evidence.

## Approach

Profile before changing controls; reuse coherent route requests, compute query
vectors once, cache immutable feature indexes by exact roster revision, batch
Store reads, and defer heavy CLI imports. Add size-tiered memory and latency
gates that preserve routing correctness and existing cold/one-call controls.

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
The cached-routing path removed redundant full-roster identity work and now
uses a recursively detached JSON-like cache clone. Five unchanged 1,000-agent
controls produced median cache-hit p95 values of 1.531, 1.595, 1.646, 1.795,
and 1.750 ms; the complete 19-test routing evaluation suite passed without
changing the 2.0 ms contract. Correctness, compatibility, roster, semantic,
selector, and the isolated 101-test distribution/release package pass. These
are fixed local controls, not cross-platform superiority or supported-runner
evidence.
