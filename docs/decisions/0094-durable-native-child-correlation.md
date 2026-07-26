---
title: "Correlate native children durably and fail Agency-planned work closed"
status: accepted
category: decisions
created: 2026-07-26
updated: 2026-07-26
tags: [routing, delegation, hooks, evidence, security]
related:
  - docs/roadmap/issue-AR-136-persist-native-child-correlation.md
  - docs/decisions/0070-run-child-specific-agency-activation.md
  - docs/decisions/0079-route-native-children-once-and-bound-unplanned-reroutes.md
  - docs/THREAT_MODEL.md
supersedes: []
superseded_by: null
id: ADR-0094
type: decision
deciders: [maintainers]
---

# ADR-0094: Correlate native children durably and fail Agency-planned work closed

## Context

Installed host hook events execute in separate processes, so an in-memory map
cannot transfer parent scope from SubagentStart to the child's later prompt.
Agency-planned labels are recognizable before Store lookup, yet lookup failure
currently becomes pass-through and allows the child to act without its planned
specialist or evidence boundary.

## Decision

Parent-child scope transfer uses a bounded durable receipt keyed by canonical
host, parent trace/session, native child identity, planned work unit, and
expiry. Creation and one-time consumption are atomic; replay, ambiguity,
identity mismatch, staleness, and unavailable evidence fail closed.

An input that matches the canonical Agency-planned label grammar is denied when
its receipt cannot be proven before tool execution. A generic host-native child
with no Agency-planned label remains pass-through and is not retroactively
claimed by Agency.

## Consequences

- Parent budgets, cache, singleflight, activation, and lineage survive real hook
  process boundaries.
- Agency-planned work cannot perform side effects outside the promised evidence
  contract.
- Store availability becomes a prerequisite only for Agency-planned children,
  not all native host delegation.
- Receipts require finite retention and cleanup.

## Alternatives

- **Keep process memory and document best effort.** Rejected because installed
  hook topology makes it predictably ineffective.
- **Encode the full parent scope in the visible label.** Rejected because labels
  are model/host visible, replayable, and size constrained.
- **Fail every native child closed on Store error.** Rejected because Agency
  must not take authority over generic host work it did not plan.
