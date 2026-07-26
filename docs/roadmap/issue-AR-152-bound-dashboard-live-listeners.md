---
title: "AR-152: Bound dashboard live-listener retention"
status: open
category: roadmap
created: 2026-07-26
updated: 2026-07-26
tags: [dashboard, performance, memory, ui]
related:
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

The live endpoint can update every 2.5 seconds. No soak assertion proves that
listener or worker-card retention remains bounded across repeated revisions.

## Approach

Delegate worker actions through one stable container listener or skip workforce
re-rendering when its revision is unchanged. Keep teardown idempotent and prove
bounded listener/card counts under repeated live updates.

## Dependencies

AR-138 and ADR-0032 own dashboard refresh lifecycle and performance behavior.

## Acceptance

- Repeated live revisions do not grow retained worker listeners or detached cards.
- Worker-detail interaction remains keyboard and pointer accessible.
- Dashboard teardown removes the bounded listener set exactly once.
- The soak regression and exact dashboard UI coverage gate pass.
