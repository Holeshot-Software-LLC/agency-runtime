---
title: "AR-138 repaired stale-error verification"
status: active
category: roadmap
created: 2026-09-07
updated: 2026-09-07
tags: [acceptance, dashboard, concurrency, browser]
related:
  - docs/roadmap/issue-AR-138-coherent-observable-dashboard-ui.md
  - docs/roadmap/acceptance/issue-AR-138.md
  - docs/roadmap/acceptance/evidence/AR-138-current-dashboard-20260907.md
  - agency_runtime/dashboard/dashboard-live.js
  - tests/dashboard_ui.test.mjs
supersedes: []
superseded_by: null
---

# AR-138 repaired stale-error verification

## Scope and candidate

First candidate fa4d042b passed browser accessibility/layout checks and isolated
criteria 2–6. Its independent criterion 1 verdict contradicted the unguarded
full-refresh catch path. All first verdicts are preserved at 25b9a67a; none were
relabeled. The original browser receipt remains an exact first-candidate record.

The same class of late error was reproduced in live polling, full refresh,
control request/commit invalidation and post-mutation reconciliation. Thirty
regression cases cover network rejection, HTTP 401 and HTTP 503, both full
refresh error-surfacing modes, replaced requests and invalidated generations.
The initial 24 cases all failed before repair. All 30 now pass, along with every
existing UI test.

Repair cd35aa2c (ledger 4fd2df4f) applies ownership/generation checks to failure paths before stale,
retry or expired-token state can be published. Live snapshot errors from an
obsolete controller return no payload; current errors still propagate. The
reconciliation wrappers preserve the false cancellation result. No current
authentication error is hidden. This JavaScript repair follows the initial
HTML/CSS accessibility/layout work; Python runtime and policy code is unchanged.

## Current verification

The full UI suite passes 172 tests, zero failures/skips, in 207.96ms. The exact
checked-in source-only coverage command passes at 96.93% lines, 86.58% branches
and 95.71% functions, above unchanged 95/86/93 floors. It also exercises current
network/authentication failures, stale successes, focus/selection restoration
and dirty forms; no existing assertion was weakened or skipped.

The first repaired run exposed an existing reconciliation-cancellation assertion
because swallowing an obsolete live error returned through its wrapper as true.
The wrappers now propagate false; that unchanged regression passes as well.

Ruff check/format (765 files) and diff checks pass. The repeated named Python
spine passes 1085 tests with three existing skips in 99.40s after the JavaScript
repair. The earlier three dashboard modules
passed 180 in 28.80s. Routing evaluation passed.

The first-candidate decision-conformance run completed with 184/184 protected
mutations killed, zero invalid/survived, source unchanged and baseline passed
in 96,869ms. It ran before the JavaScript race repair; no Python decision,
mutation definition or selected Python test changed afterward. That receipt is
not presented as a fresh post-repair mutation run. No exhaustive corpus,
coverage matrix, interpreter matrix or hosted workflow was dispatched.

## Browser evidence

The rebuilt wheel was installed into a new disposable target and tested at
2026-09-07T05:15:13.514Z. The real packaged HTTP server served all ten packaged
dashboard assets; each asset's SHA-256 matched the repaired source. No owner's
dashboard profile, host activation, provider credential or native runtime was
used. Host inventory was stubbed and server outbound connections were denied.

Wheel SHA-256:

    45b38a0873bb7730213bf587970782f5c130ff81394f7e1d85a73aded4db5db3

Chromium 152.0.7977.64 (sandbox enabled), Playwright 1.63.0 and axe-core 4.13.0
returned exit 0 and passed=true. Seven fully loaded sections were checked at
each viewport: overview, routing, evidence, roster, workforce, hosts, settings.

| Viewport | View checks | Axe violations | Page overflow | Clipped metrics |
|---|---|---|---|---|
| 1280 x 900 | 7 | 0 | none | 0 |
| 1024 x 768 | 7 | 0 | none | 0 |
| 375 x 812 | 7 | 0 | none | 0 |

Each viewport additionally required an actual control request while preserving
the unsaved focused field, selection range, field value and all open settings
details. Keyboard scrolling worked. A deliberately aborted control request
retained the last good revision, visibly marked it stale, and emitted the same
valid UUIDv4 in the UI notice and application console. Removing the fault and
refreshing restored fresh state. Unexpected console/page/HTTP errors were zero.

Correlated failure IDs: 5d8fa563-26c5-4f0a-9700-d309d12728e1 (1280),
d56125aa-bc50-4677-b512-3b1f4c8c280f (1024), and
66d428bf-e328-406a-934a-20da73a3bb7d (375).

Artifacts: [repaired JSON report](AR-138-browser-repaired-20260907/report.json),
[desktop](AR-138-browser-repaired-20260907/1280-overview.png),
[intermediate](AR-138-browser-repaired-20260907/1024-overview.png),
[375 px](AR-138-browser-repaired-20260907/375-overview.png).

Report SHA-256:

    da108261451e472377efbb04f41bc8d1d13a6b3f9a6977c9627f1b6d13612d2e

Axe's WCAG 2.0/2.1 A/AA scan retains incomplete contrast checks for gradients,
pseudo-elements, overlaps and short text, not silent passes. The bounded
automated check is not a full WCAG or screen-reader certificate. The first
candidate's receipt remains intact and is not substituted for this repaired one.

The existing [reproduction procedure](AR-138-current-dashboard-20260907.md#reproduction)
and unchanged optional checker apply. Keep the first receipt intact. This is
private installed-wheel dashboard QA, not native-host activation, every dataset,
screen-reader or full WCAG certification.
