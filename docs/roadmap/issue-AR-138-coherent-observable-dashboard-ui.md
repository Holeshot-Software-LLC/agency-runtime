---
title: "AR-138: Make dashboard refresh coherent, accessible, and observable"
status: open
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

The original coherence, stale-state, focus, duplicate-render, accessible-name,
and request-correlation fixes exist. September 7 packaged-browser review also
confirms that the earlier mobile heading-basis fix exists at 375 px. The July
test counts below are historical, not a current closure receipt.

Current browser review reproduced low-contrast navigation/empty-state text,
unfocusable scroll regions, unnamed generic groups, and clipped metric cards
inside desktop half-width panels. The bounded repair uses existing accessible
colors, named keyboard-focusable scroll regions, group roles, and a wrapping
metric grid. Four focused regressions pass after failing before repair.
The three dashboard Python modules pass 180 tests; the named production spine
passes 1085 with three existing skips (69.50s). No staffing or host policy changes.

Package state: live_demo complete, acceptance pending. The optional browser checker uses a freshly
installed wheel, private five-agent Store, stubbed host inventory and denied
outbound server connections. The final view-loaded browser receipt passes all
21 view/viewport cases with zero axe violations, page overflow, clipped metric
cards or unexpected console/HTTP errors. Actual control polls preserve focus,
selection and open details; injected failures retain the last revision, show
safe correlated IDs and recover. All 142 UI tests pass. Exact hashes, versions,
screenshots, commands and limits are in the linked current evidence. The record
stays open; no full WCAG/native-host claim. The first isolated review satisfies
criteria 2–6 but contradicts criterion 1: full-refresh success is generation
guarded, while a replaced request's late non-abort error can still overwrite a
newer healthy connection. Preserve those verdicts and repair both success/error
generation boundaries consistently before re-verification. The complete first
review is preserved at 25b9a67a. Thirty added late-failure cases now pass after
repairing live/full/control failure guards and reconciliation cancellation;
the full 172-test UI suite passes. Repair cd35aa2c's rebuilt wheel also passes
all 21 browser checks, with ten matching asset hashes and repeated focus/error
assertions. Current network/authentication failures still surface. The second
isolated acceptance pass is the remaining gate before closure and PR #700 merge.

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

- [ ] Out-of-order responses cannot overwrite newer state.
- [ ] Partial refresh failure is visible and never presented as fresh.
- [ ] Related control panels share one declared revision.
- [ ] Polling preserves keyboard focus, open details, and selection.
- [ ] Automated accessibility, desktop, and 375 px mobile tests pass.
- [ ] Browser console and network failures surface a safe request ID.

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
