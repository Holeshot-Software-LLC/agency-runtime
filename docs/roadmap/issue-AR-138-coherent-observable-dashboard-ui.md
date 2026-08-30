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

The original coherence, stale-state, focus, duplicate-render, accessible-name,
and request-correlation defects are repaired. Fresh installed-artifact review
then exposed one responsive regression: the desktop heading flex basis became a
280 px vertical basis after the mobile layout changed to a column. The source
fix now resets that basis at the mobile breakpoint; final packaged-candidate QA
remains before this item can close.

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
post-install desktop/mobile browser QA found the mobile heading-basis defect.
Commit `9aa317c` adds the breakpoint override and a CSS contract regression. The
current 106-test coverage gate passes at 98.74 percent lines, 90.70 percent
branches, and 97.98 percent functions. A live 390 x 844 source recheck reduced
the topbar from 521 px to 297 px, reduced the heading from 280 px to 56 px,
moved controls from y=387 to y=173, retained a clean desktop layout, and emitted
no browser warnings or errors. The next packaged candidate still needs the
same bounded desktop/mobile recheck.
