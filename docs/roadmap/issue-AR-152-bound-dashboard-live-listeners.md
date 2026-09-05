---
title: "AR-152: Bound dashboard live-listener retention"
status: done
category: roadmap
created: 2026-07-26
updated: 2026-09-05
tags: [dashboard, performance, memory, ui]
related:
  - docs/decisions/0220-measure-dashboard-coverage-over-production-modules.md
  - docs/roadmap/issue-AR-406-restore-dashboard-function-coverage.md
  - docs/roadmap/acceptance/issue-AR-152.md
  - docs/roadmap/acceptance/evidence/AR-406-production-coverage-20260905.md
  - docs/decisions/0032-adaptive-authenticated-dashboard-polling.md
  - docs/roadmap/issue-AR-138-coherent-observable-dashboard-ui.md
  - agency_runtime/dashboard/dashboard-render.js
supersedes: []
superseded_by: null
type: issue
epic: performance
issue_id: AR-152
priority: p1
tracker_url: null
depends_on: []
blocks: []
---

# AR-152: Bound dashboard live-listener retention

## Problem

Each live workforce render creates worker buttons and retains their listener
closures in a global disposer list. Removed DOM nodes remain reachable until
dashboard teardown, causing listener and object growth on every polling cycle.

## Current state

The 6a3bdaa repair is present: one delegated container listener serves native
worker buttons, and teardown drains its disposer exactly once. The existing
50-revision soak verifies no per-card listeners, one stable container listener,
working nested-label selection and no listener after teardown. All 138 UI cases
pass. AR-406 corrects the shared coverage measurement to all seven production
modules under ADR-0220; unchanged 95/86/93 floors pass at 96.92/86.62/95.71.
No listener implementation change is needed. All four isolated criteria are
satisfied at candidate 12a62393.

## Approach

Delegate worker actions through one stable container listener or skip workforce
re-rendering when its revision is unchanged. Keep teardown idempotent and prove
bounded listener/card counts under repeated live updates.

## Dependencies

AR-138 and ADR-0032 own dashboard refresh lifecycle and performance behavior.

## Acceptance

- [x] Repeated live revisions do not grow retained worker listeners or detached cards.
- [x] Worker-detail interaction remains keyboard and pointer accessible.
- [x] Dashboard teardown removes the bounded listener set exactly once.
- [x] The soak regression and exact dashboard UI coverage gate pass.

## Implementation evidence

Commit `6a3bdaa` replaces per-render worker closures with a stable delegated
listener whose disposer is registered once and removed idempotently at
teardown. Repeated-revision soak and keyboard/pointer regressions keep the
listener set bounded while preserving worker-detail behavior. The dashboard UI
suite passed all 101 tests; full current-artifact and aggregate release evidence
remain.
