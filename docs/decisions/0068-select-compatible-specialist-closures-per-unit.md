---
title: "Select compatible specialist closures per work unit"
status: accepted
category: decisions
created: 2026-07-18
updated: 2026-07-18
tags: [routing, compatibility, delegation, work-units, dag]
related:
  - docs/roadmap/issue-AR-58-unit-aware-delegation-assignment.md
  - docs/roadmap/issue-AR-82-full-roster-unit-routing.md
  - docs/roadmap/issue-AR-84-bounded-semantic-agent-cards.md
  - docs/decisions/0054-unit-aware-assignment-and-event-driven-dag.md
  - docs/worklog/README.md
supersedes: [docs/decisions/0054-unit-aware-assignment-and-event-driven-dag.md]
superseded_by: null
id: ADR-0068
type: decision
deciders: [maintainers]
---

# ADR-0068: Select compatible specialist closures per work unit

## Context

A small checked-in token map can assign already-selected specialists
deterministically, but it imposes a global recall ceiling and can fall back to a
resident manager as if the manager were a domain worker. Independently choosing
several top scorers also ignores requirements and conflicts between agents.

## Decision

Route each bounded work unit against the full revision-stable approved and
enabled catalog before prompt hydration. After hard eligibility filtering,
construct the smallest sufficient compatible specialist closure jointly.
Dependencies declared through `requires` are atomic: include the complete
eligible closure or reject the proposal. Enforce `conflicts_with`, authority,
context mode, independence, host, platform, tool, permission, and resource
constraints during construction.

Optimize capability coverage, calibrated confidence, evidence quality, and
useful independent review while minimizing conflict, duplicated work,
coordination cost, latency, and token use. `max_selected` limits optional root
specialists, not required dependency closure. A specifically requested isolated
reviewer may exceed the root limit only through the explicit reviewer rule.

Persist the exact catalog revision, compatibility algorithm version, work-unit
ID, selected closure, rationale, and relevant constraint receipts for replay.
No-match and resident-managers-only are valid parent outcomes; resident managers
are never assigned as domain workers.

Preserve the validated event-driven native-work DAG behavior from ADR-0054:
successful predecessors release their own dependents, independent branches may
progress concurrently, and failed or missing outcomes skip descendants. Agency
recommends the graph; the native host owns scheduling and worktrees.

## Consequences

- Every approved agent remains eligible for the work unit it best fits.
- Required companions cannot be half-selected.
- Coordinator fallback no longer masquerades as specialist execution.
- Deterministic replay is tied to the exact roster and compatibility versions.
- Set construction costs more than independent top-k sorting but remains bounded
  by filtered candidates and deterministic budgets.

## Alternatives

- Assign only from the global top-k set. Rejected because omitted specialists
  cannot win a later work unit.
- Choose independent top scorers and concatenate them. Rejected because
  compatibility is a set property.
- Use resident managers as unmatched unit workers. Rejected because they own
  management, not domain execution.
