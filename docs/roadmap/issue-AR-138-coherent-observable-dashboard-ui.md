---
title: "AR-138: Make dashboard refresh coherent, accessible, and observable"
status: open
category: roadmap
created: 2026-07-26
updated: 2026-07-27
tags: [dashboard, ui, accessibility, concurrency, observability]
related:
  - agency_runtime/dashboard
  - agency_runtime/server/dashboard.py
  - docs/roadmap/issue-AR-144-restore-dashboard-ui-release-coverage.md
  - docs/decisions/0032-adaptive-authenticated-dashboard-polling.md
supersedes: []
superseded_by: null
type: issue
epic: dashboard
issue_id: AR-138
priority: p1
tracker_url: null
depends_on: []
blocks:
  - AR-144
  - AR-170
---

# AR-138: Make dashboard refresh coherent, accessible, and observable

## Problem

Failed control refreshes are swallowed, parallel responses can compose mixed
revisions, older asynchronous reads can overwrite newer user intent, and
polling replaces focused/open DOM nodes. One provider-model field lacks an
accessible name.

## Current state

Server-side CAS protects mutation integrity, so no stale write was reproduced.
The visible dashboard can still show a stale or internally mixed state, lose
focus/details, double-render workforce panels, and provide only a short generic
toast without a request identifier.

## Approach

Use generation tokens or AbortController for every mutable view, commit related
panels from one coherent response, retain the last good state with an explicit
stale/error marker, preserve focus and disclosure state during polling, and
surface a bounded safe request ID for support.

## Dependencies

AR-142 defines server-side request instrumentation. AR-137 owns pagination.

## Acceptance

- Out-of-order responses cannot overwrite newer state.
- Partial refresh failure is visible and never presented as fresh.
- Related control panels share one declared revision.
- Polling preserves keyboard focus, open details, and selection.
- Automated accessibility, desktop, and 375 px mobile tests pass.
- Browser console and network failures surface a safe request ID.

## Implementation evidence

One /api/control response now binds configuration, hosts, roster, governance,
Store identity, and a control revision. The client validates the complete
snapshot before mutating state, rejects stale generations, aborts obsolete
requests, retains last-good state with an explicit stale marker and safe request
ID, preserves focus/selection/disclosure state, and commits workforce plus
control state before one render. Browser IDs are canonical UUIDv4 values and
the server echoes the shared Agency request ID. The exact release-coverage
suite passes all 84 tests at 97.13 percent lines, 91.28 percent branches, and
96.32 percent functions; the server suite passes 134 with 3 skips. Fresh
post-install desktop/mobile browser QA remains required.
