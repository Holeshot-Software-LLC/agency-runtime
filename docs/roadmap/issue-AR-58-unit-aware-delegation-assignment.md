---
title: "AR-58: Assign each delegation unit to its best specialist"
status: done
category: roadmap
created: 2026-07-16
updated: 2026-07-18
tags: [delegation, routing, specialists, correctness, determinism]
related:
  - docs/decisions/0054-unit-aware-assignment-and-event-driven-dag.md
  - docs/decisions/0011-explicit-delegation-evidence-lifecycle.md
  - docs/decisions/0019-bounded-machine-readable-cli-delegation.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: routing
issue_id: AR-58
priority: p0
tracker_url: "https://github.com/Holeshot-Software-LLC/agency-runtime/issues/59"
depends_on: [AR-27, AR-30]
blocks: [AR-59, AR-81, AR-82, AR-87]
---

# AR-58: Assign each delegation unit to its best specialist

## Problem

A multi-part request can select several specialists, but assigning every work
unit to the first selected slug throws away that routing information. The
result is misleading delegation evidence and lower execution quality whenever
the units need different capabilities.

## Current state

Each bounded detected work unit now receives its own deterministic assignment.
The assignment scores unit vocabulary against selected specialist identities
and role signals, preserves selection order as a stable tie-breaker, and uses a
protected coordinator only when no substantive selected specialist matches.
The same versioned unit plan feeds preflight context and durable suggestions.

## Approach

Build one bounded `work_unit_id -> recommended_agent` plan at preflight. Exclude
the coordinator fallback from substantive specialist scoring, choose the
highest positive match deterministically, and fall back to
`agents-orchestrator` then `chief-of-staff` when necessary and available. Keep
assignment versioning explicit so evaluation changes cannot masquerade as the
same policy.

## Dependencies

AR-27 supplies authoritative delegation outcomes, and AR-30 supplies bounded
work-unit text without breaking verb-shaped noun phrases. ADR-0054 governs the
shared plan and its execution order.

## Acceptance

- [x] Every detected unit is assigned independently rather than to the first selected agent.
- [x] Assignment is bounded, versioned, deterministic, and stable under ties.
- [x] A substantive unit prefers a matching selected specialist.
- [x] Unmatched units use only an available protected coordinator fallback.
- [x] Preflight context and persisted delegation suggestions use the same plan.
- [x] Duplicate and empty units do not create duplicate assignments.
