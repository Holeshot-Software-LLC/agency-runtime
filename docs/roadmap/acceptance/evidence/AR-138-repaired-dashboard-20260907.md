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

The repair applies ownership/generation checks to failure paths before stale,
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

The repaired wheel and final browser receipt are pending at this source
checkpoint. Do not use the first-candidate screenshots to certify the changed
JavaScript. Rebuild, install into a new disposable target, and repeat the same
21 view-loaded checks plus real-poll focus preservation and failure/recovery
before freezing the second isolated acceptance candidate.

The existing [reproduction procedure](AR-138-current-dashboard-20260907.md#reproduction)
and unchanged optional checker apply. Keep the first receipt intact. This is
private installed-wheel dashboard QA, not native-host activation, every dataset,
screen-reader or full WCAG certification.
