---
title: "AR-150: Coordinate dashboard refresh commit epochs"
status: open
category: roadmap
created: 2026-07-26
updated: 2026-07-26
tags: [dashboard, concurrency, ui, traceability]
related:
  - docs/decisions/0032-adaptive-authenticated-dashboard-polling.md
  - docs/roadmap/issue-AR-138-coherent-observable-dashboard-ui.md
  - agency_runtime/dashboard/dashboard-live.js
supersedes: []
superseded_by: null
type: issue
epic: dashboard
issue_id: AR-150
priority: p0
tracker_url: null
depends_on: []
blocks: []
---

# AR-150: Coordinate dashboard refresh commit epochs

## Problem

View-scoped filter and workforce requests coordinate only within their own
scope. An older periodic control-plane or full refresh can commit afterward and
overwrite newer user intent; the inverse race can also compose stale state.

## Current state

Per-scope abort and generation checks prevent same-scope stale commits, but no
shared commit epoch orders control, full, and view-scoped updates.

## Approach

Capture one monotonic UI intent/commit epoch across refresh scopes. Discard a
response whenever a newer relevant user intent or authoritative commit has
superseded its capture, without weakening last-good-state behavior.

## Dependencies

AR-138 and ADR-0032 define the coherent refresh and adaptive polling contract.

## Acceptance

- Deferred cross-scope responses cannot overwrite newer filters or worker views.
- The inverse response order cannot compose incompatible revisions.
- Last-good state, abort handling, focus preservation, and stale indicators remain correct.
- Exact dashboard UI coverage floors and server integration tests pass.
