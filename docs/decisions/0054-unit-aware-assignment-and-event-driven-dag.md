---
title: "Use unit-aware specialist assignment and event-driven DAG scheduling"
status: superseded
category: decisions
created: 2026-07-16
updated: 2026-07-18
tags: [delegation, routing, dag, concurrency, performance]
related:
  - docs/roadmap/issue-AR-58-unit-aware-delegation-assignment.md
  - docs/roadmap/issue-AR-59-event-driven-delegation-scheduler.md
  - docs/decisions/0011-explicit-delegation-evidence-lifecycle.md
  - docs/decisions/0019-bounded-machine-readable-cli-delegation.md
  - docs/worklog/README.md
supersedes: []
superseded_by: docs/decisions/0068-select-compatible-specialist-closures-per-unit.md
id: ADR-0054
type: decision
deciders: [maintainers]
---

# ADR-0054: Use unit-aware specialist assignment and event-driven DAG scheduling

## Context

A route may select several specialists for a request containing several
independent work units. Assigning the first selected specialist to every unit
is deterministic but wrong: it discards the unit's subject and records a
recommendation that the router did not actually make. Separately, dispatching
an otherwise valid dependency graph in topological batches makes a fast branch
wait for unrelated slow work at the same level.

Correct assignment and efficient scheduling must remain bounded and auditable.
They cannot introduce a second hidden planner, relax dependency success, or
allow thread timing to make durable suggestions nondeterministic.

## Decision

Build one versioned, bounded unit-assignment plan during preflight. For each
normalized work unit, score the non-coordinator selected specialist slugs using
exact tokens and a small checked-in role-signal map. Choose the highest positive
score, preserving selected order and then slug order as deterministic
tie-breakers. If no substantive specialist matches, choose the first available
protected fallback in the fixed order `agents-orchestrator`, then
`chief-of-staff`. Preflight context and durable suggestions consume this same
plan.

Execute the validated DAG with a bounded event-driven scheduler. Track each
node's remaining predecessor count, keep ready unit IDs in a stable priority
queue, fill at most the configured worker count, and react to the first
completed future. A child becomes ready immediately after all of its own
predecessors complete successfully. A failed, malformed, or missing result
recursively skips its descendants while independent branches continue.
Simultaneously completed units are processed in stable unit-ID order.

Topological batches remain useful diagnostic output, not an execution barrier.
The scheduler validates units, graph nodes, worker bounds, backend resolution,
and delegate compatibility before creating worktrees or invoking delegated
work. If shorthand numbered input also contains dependency language that the
current structured work-unit schema cannot represent faithfully, detection
fails closed instead of erasing the implied edges and dispatching independent
work.

## Consequences

- Delegation evidence names a specialist suited to each individual unit.
- Fallback coordinators remain explicit and do not masquerade as a substantive
  route match.
- A fast dependency chain can progress while an unrelated branch is still
  running, improving bounded-worker utilization and latency.
- Dependency success remains strict; concurrency cannot release a child from a
  merely present or truthy result.
- Unrepresentable mixed dependency syntax produces no unsafe partial plan.
- Deterministic queues, tie-breakers, and assignment versioning keep evaluation
  and durable evidence reproducible.
- The checked-in role-signal map is deliberately small and must change through
  evaluated, versioned policy work rather than opaque runtime inference.

## Alternatives

- Assign every unit to the first selected specialist. Rejected because it
  throws away unit-specific routing information.
- Ask another model to assign units. Rejected because it adds latency,
  nondeterminism, provider dependency, and a new uncorrelated evidence source.
- Execute one topological level at a time. Rejected because unrelated slow work
  becomes an artificial barrier.
- Release dependents after any predecessor result. Rejected because only an
  authoritative successful result satisfies a dependency.
