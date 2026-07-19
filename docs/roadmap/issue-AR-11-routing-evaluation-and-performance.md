---
title: "AR-11: Establish routing accuracy and performance gates"
status: done
category: roadmap
created: 2026-07-10
updated: 2026-07-18
tags: [routing, evaluation, performance]
related:
  - docs/decisions/0001-layered-specialist-routing.md
  - docs/decisions/0015-versioned-selection-explain-receipts.md
  - docs/decisions/0021-full-companion-policy-with-precedence.md
  - docs/decisions/0030-versioned-quantitative-evaluation-gates.md
supersedes: []
superseded_by: null
type: issue
epic: testing
issue_id: AR-11
priority: p0
tracker_url: "https://github.com/Holeshot-Software-LLC/agency-runtime/issues/11"
depends_on: []
blocks: [AR-07, AR-84, AR-88]
---

# AR-11: Establish routing accuracy and performance gates

## Problem

Passing unit tests does not establish that specialist selection and delegation
detection are accurate, stable across roster changes, or fast under concurrent
production load. Current heuristics can select unrelated agents, reuse stale
cache and session state, and report incomplete provider latency.

## Current state

Cache and stickiness state now use a stable fingerprint of the roster, full
routing/provider configuration, and policy. Reused results refresh work units,
state is bounded and thread-safe, candidate scoring includes categories and
capabilities, policy matching is boundary-aware, and zero-signal fallback
abstains.

`agency eval routing` now runs the v1.2 offline corpus with 31 routing, 25
policy, and 17 delegation cases plus deterministic 1,000-agent and concurrent
benchmarks. The report gates policy macro F1, delegation precision, recall, and
dependency-graph accuracy, required Recall@3, abstention, forbidden matches,
cold and cache-hit latency, concurrent throughput and overlap, determinism, and
unique per-request traces.

The concurrency probe synchronizes workers only after each call has progressed
inside real candidate narrowing through catalog compilation and first-agent
scoring. This removes dependence on the CPython thread-switch interval while
still failing when a lock serializes narrowing before that point. The release
gate requires both overlap and a fully synchronized internal probe.

The production-readiness run passed every gate: required Recall@3 and top-one
accuracy were 1.0, policy macro F1 was 0.9921, delegation precision, recall,
and graph accuracy were 1.0, 1,000-agent p95 was 7.584 ms, cache-hit p95 was
0.582 ms, and 32 concurrent requests completed deterministically without trace
reuse.

## Approach

Create versioned routing, policy-adversarial, sequence, provider-fault,
delegation, lifecycle, and evidence datasets. Refactor routing around one
immutable decision trace and a roster/config/policy fingerprint, then enforce
accuracy, abstention, determinism, concurrency, and latency thresholds in CI.

## Dependencies

None. Dataset construction and correctness refactoring can proceed together;
release readiness depends on the resulting gates.

## Acceptance

- [x] Cache reuse is impossible across different roster/config/policy fingerprints.
- [x] Zero-signal requests abstain instead of selecting arbitrary agents.
- [x] Required-specialist Recall@3 is at least 97 percent on the locked corpus.
- [x] Policy macro F1 is at least 95 percent with adversarial minimal pairs.
- [x] Delegation precision is at least 95 percent and recall at least 90 percent.
- [x] Dependency-graph accuracy is 100 percent for versioned sequencing cases.
- [x] Local routing p95 is below 20 ms at 1,000 agents and cache-hit p95 below 2 ms.
- [x] Thirty-two concurrent requests show no contamination, exceptions, or stale selections.

## Concurrency-flake verification

- The former outer-call counter failed 2 of 20 runs at the default 5 ms Python
  switch interval and 20 of 20 runs at 50 ms.
- The internal probe passed 20 of 20 runs at 1 ms, 5 ms, and 50 ms, plus 20 of
  20 runs with four CPU-load threads.
- Ten repeated complete routing evaluations passed with eight of eight workers
  reaching the internal probe on every run.
- A serialized-wrapper regression test produces overlap 1 and fails probe
  synchronization, proving the barrier does not hide real serialization.
