---
title: "Route native children once and bound unplanned reroutes"
status: accepted
category: decisions
created: 2026-07-21
updated: 2026-07-21
tags: [routing, delegation, performance, native-hosts]
related:
  - docs/roadmap/issue-AR-116-bound-child-routing-and-oauth-model-selection.md
  - docs/decisions/0067-require-configured-inference-for-selection.md
  - docs/decisions/0069-enforce-conflicts-before-prompt-composition.md
  - docs/decisions/0070-run-child-specific-agency-activation.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
id: ADR-0079
type: decision
deciders: [maintainers]
---

# ADR-0079: Route native children once and bound unplanned reroutes

## Context

Codex, Claude Code, OpenClaw, and Hermes own their native child schedulers.
Agency improves those children by supplying assignment-specific specialist
instructions, but it must not replace the scheduler or multiply a large native
fan-out into the same number of inference calls. A process-local limit is not
enough because host hooks and services may run in separate processes.

## Decision

The parent routes every planned work unit once. Its native child consumes an
exact-version, one-use specialist activation and performs no independent Agency
selection. An unplanned native child may request selection only with explicit
parent correlation.

Unplanned requests coordinate through the canonical SQLite store. The store
holds a parent-scoped inference-call budget, a parent-scoped concurrency limit,
an expiring cross-process lease for singleflight, and an expiring content-free
routing cache. Cache keys contain hashes and routing identities, never the
assignment text. Defaults are four new inference calls per parent, two
concurrent calls, and a fifteen-minute cache.

If configured inference cannot run because the budget or concurrency limit is
exhausted, deterministic retrieval may produce diagnostics but Agency abstains
from selecting a specialist. This preserves the rule that configured inference
is authoritative while allowing resident managers and the native host to keep
working. When inference is not configured, the normal deterministic path
remains available.

## Consequences

- A host can fan out many children without creating an unbounded inference fan-out.
- Duplicate assignments across processes share one result.
- Planned children remain faster because they do not reroute work the parent already classified.
- Native scheduling remains owned by each host.
- Operators can tune the budget, concurrency, and cache lifetime from the same configuration used by the CLI and dashboard.
- Over-budget unplanned children may receive no specialist rather than an unverified one.

## Alternatives

- **Let every child infer independently.** Rejected because cost and latency scale directly with native fan-out.
- **Disable Agency in native children.** Rejected because assignment-specific expertise is one of the central product goals.
- **Create an Agency-owned worker pool.** Rejected because it would compete with native host scheduling and lifecycle evidence.
- **Use only an in-process semaphore and cache.** Rejected because host hooks and services do not share process memory.

