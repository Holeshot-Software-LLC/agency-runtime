---
title: "AR-150: Coordinate dashboard refresh commit epochs"
status: open
category: roadmap
created: 2026-07-26
updated: 2026-09-07
tags: [dashboard, concurrency, ui, traceability]
related:
  - docs/decisions/0032-adaptive-authenticated-dashboard-polling.md
  - docs/decisions/0220-measure-dashboard-coverage-over-production-modules.md
  - docs/roadmap/issue-AR-138-coherent-observable-dashboard-ui.md
  - docs/roadmap/issue-AR-404-evidence-led-backlog-completion.md
  - docs/roadmap/acceptance/evidence/AR-150-refresh-epochs-20260907.md
  - docs/roadmap/acceptance/evidence/AR-150-inverse-order-proof-20260907.md
  - docs/roadmap/acceptance/issue-AR-150.md
  - docs/worklog/README.md
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

September 7 review confirms the shared commit epoch and lifecycle-bound request
scopes already exist. Beginning a view request invalidates pending control/full
and older view work; beginning a full refresh invalidates pending view work.
Every view commit checks its captured epoch/controller, and full/control reads
check the same epoch before applying any state. AR-138's cd35aa2c repair also
guards obsolete error paths. No production change is needed in this package.

Fresh UI coverage passes all 172 tests (227.66ms) with 96.93/86.58/95.71 above
the unchanged current 95/86/93 floors; dashboard server/auth/transaction tests
pass 180 (28.82s). Source/test/script equality to 2ecde1a5 binds the existing
21-case installed-wheel browser evidence, including real polling interaction
preservation and stale-state recovery. Exact scope and citations are in the
linked evidence. First isolated acceptance satisfies criteria 1, 3 and 4, but
criterion 2 is absent: the cited tests do not directly demonstrate inverse
refresh-response ordering. Preserve the supplied verdicts and add a direct
deferred-response regression before a second pass; no code defect is asserted.
The first review is preserved at 4e820ff4. Four new direct cases now cover
workforce/full refresh in both directions and both completion orders, delivering
old responses even after abort. All four and the full 176-test UI suite pass;
coverage is 96.93/86.70/95.71. No runtime change; freeze this proof for review.

The original report's absent-epoch state was pre-repair. The July implementation
receipt below is historical; its blanket final aggregate-release requirement
does not override the current bounded-delivery policy.

## Approach

Capture one monotonic UI intent/commit epoch across refresh scopes. Discard a
response whenever a newer relevant user intent or authoritative commit has
superseded its capture, without weakening last-good-state behavior.

## Dependencies

AR-138 and ADR-0032 define the coherent refresh and adaptive polling contract.

## Acceptance

- [ ] Deferred cross-scope responses cannot overwrite newer filters or worker views.
- [ ] The inverse response order cannot compose incompatible revisions.
- [ ] Last-good state, abort handling, focus preservation, and stale indicators remain correct.
- [ ] Exact dashboard UI coverage floors and server integration tests pass.

## Implementation evidence

Commit `6a3bdaa` coordinates control, full, and view-scoped work under one
monotonic commit epoch and lifecycle-bound request scopes. Mutation-resistant
UI regressions prove that either cross-scope completion order preserves the
newest compatible state, including last-good and focus behavior. The shared
focused package passed 168 Python tests with 3 skips, four post-review
regressions, and 101 dashboard UI tests. Final current-artifact and aggregate
release evidence remain.
