---
title: "AR-138: Make dashboard refresh coherent, accessible, and observable"
status: done
category: roadmap
created: 2026-07-26
updated: 2026-09-07
tags: [dashboard, ui, accessibility, concurrency, observability]
related:
  - agency_runtime/dashboard
  - agency_runtime/server/dashboard.py
  - docs/roadmap/issue-AR-144-restore-dashboard-ui-release-coverage.md
  - docs/decisions/0032-adaptive-authenticated-dashboard-polling.md
  - scripts/verify_dashboard_browser.py
  - scripts/verify_dashboard_browser.mjs
  - docs/roadmap/issue-AR-404-evidence-led-backlog-completion.md
  - docs/worklog/README.md
  - docs/roadmap/acceptance/issue-AR-138.md
  - docs/roadmap/acceptance/evidence/AR-138-current-dashboard-20260907.md
  - docs/roadmap/acceptance/evidence/AR-138-repaired-dashboard-20260907.md
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

All six original criteria have satisfied isolated verdicts against repaired
candidate 2ecde1a5 on September 7. The original coherence, focus, request-ID and
mobile heading fixes were present. Browser review found remaining contrast,
keyboard-scroll/semantic and desktop metric-clipping defects, repaired at
d7231df3 with four regressions. The first isolated review then exposed a late
error from an obsolete refresh overwriting newer healthy connection state;
that complete review is preserved at 25b9a67a, not relabeled as a pass.

Repair cd35aa2c guards live/full/control failures and propagates cancellation.
Thirty added late-failure cases and all 172 UI tests pass; current network and
authentication failures still surface. Dashboard Python checks pass 180; the
repeated named production spine passes 1085 with three existing skips (99.40s).
UI coverage meets the unchanged 95/86/93 floors. The earlier conformance run
killed 184/184 mutations with source unchanged; no Python decision code or
selected test changed in the subsequent JavaScript repair.

The rebuilt wheel passes 21 loaded-view checks at 1280/1024/375 px, with ten
matching asset hashes, zero axe violations, no clipped metrics/page overflow,
and no unexpected console/HTTP errors. Actual polls preserve focus, selection
and open details; injected failures retain the revision, show correlated safe
IDs and recover. The fixture uses a private five-agent Store, stubbed host
inventory and denied outbound server connections. Exact versions, hashes,
screenshots and limits are in the repaired evidence. This is not full WCAG,
screen-reader or native-host certification. No staffing/host policy change.
Scoped package accepted and merged through PR #700 at 1ada216c on September 7,
05:28:53Z. The exact publication receipt is in the worklog.

## Approach

Use generation tokens or AbortController for every mutable view, commit related
panels from one coherent response, retain the last good state with an explicit
stale/error marker, preserve focus and disclosure state during polling, and
surface a bounded safe request ID for support.

Finish the September 7 package with wheel-backed desktop, intermediate-width
and 375 px browser checks, capture their exact asset hashes and screenshots,
then obtain isolated acceptance. Browser QA tooling is optional development
tooling outside the runtime; no frontend framework/build/CDN dependency is added.

## Dependencies

AR-142 defines server-side request instrumentation. AR-137 owns pagination.

## Acceptance

- [x] Out-of-order responses cannot overwrite newer state.
- [x] Partial refresh failure is visible and never presented as fresh.
- [x] Related control panels share one declared revision.
- [x] Polling preserves keyboard focus, open details, and selection.
- [x] Automated accessibility, desktop, and 375 px mobile tests pass.
- [x] Browser console and network failures surface a safe request ID.

## Historical implementation evidence (July)

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
