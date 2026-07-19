---
title: "AR-82: Route each delegated work unit against the full active roster"
status: in_progress
category: roadmap
created: 2026-07-17
updated: 2026-07-18
tags: [routing, delegation, roster, replay, performance]
related:
  - docs/decisions/0054-unit-aware-assignment-and-event-driven-dag.md
  - docs/decisions/0062-isolate-directives-and-route-units-first.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: routing
issue_id: AR-82
priority: p0
tracker_url: "https://github.com/Holeshot-Software-LLC/agency-runtime/issues/82"
depends_on: [AR-58, AR-59]
blocks: [AR-84, AR-87]
---

# AR-82: Route each delegated work unit against the full active roster

## Problem

Unit assignment previously searched only the small globally selected set. A
specialist omitted from that set could never win the unit it was best suited to,
creating a hard recall ceiling before delegation began.

## Current state

Implementation is moving unit assignment to bounded deterministic narrowing over
the full revision-stable active catalog. Exact assignment winners are persisted
for replay while older recipes remain readable. Final performance and integrated
verification remain in progress.

## Approach

Decompose first, route every bounded unit independently over the same active
catalog snapshot, then hydrate only the winners needed by the delivery mode.
Persist content-free assignment identities and version the assignment recipe so
replay never silently re-routes a completed preflight.

## Dependencies

AR-58 defines unit assignment and AR-59 defines the event-driven dependency DAG.

## Acceptance

- [ ] A globally omitted specialist can win its matching work unit.
- [ ] Assignment searches the full active catalog snapshot.
- [ ] Replay preserves exact bounded winners and reads prior recipes safely.
- [ ] Large-roster selection remains within the performance budget.
- [ ] Full branch and merged-install gates pass.
