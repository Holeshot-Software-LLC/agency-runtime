---
title: "AR-175: Retire the non-atomic dashboard control fallback"
status: in_progress
category: roadmap
created: 2026-07-27
updated: 2026-09-07
tags: [dashboard, traceability, performance, compatibility, security]
related:
  - docs/roadmap/acceptance/evidence/AR-175-control-boundary-20260907.md
  - docs/roadmap/issue-AR-404-evidence-led-backlog-completion.md
  - docs/decisions/0105-bound-delivery-to-live-demo-checkpoints.md
  - docs/decisions/0029-secure-local-dashboard-and-bounded-observability.md
  - docs/decisions/0032-adaptive-authenticated-dashboard-polling.md
  - docs/decisions/0095-complete-paginated-dashboard-collections.md
  - docs/roadmap/issue-AR-170-fail-dashboard-response-correlation-closed.md
  - docs/roadmap/issue-AR-172-make-roster-pages-snapshot-consistent.md
  - agency_runtime/dashboard/dashboard-live.js
  - tests/dashboard_ui.test.mjs
  - tests/test_release_packaging.py
supersedes: []
superseded_by: null
type: issue
epic: dashboard
issue_id: AR-175
priority: p1
tracker_url: null
depends_on: [AR-170, AR-172]
blocks: []
---

# AR-175: Retire the non-atomic dashboard control fallback

## Problem

The current dashboard and server ship as one versioned package and the server
always exposes the atomic `agency.dashboard.control.v1` envelope. The browser
nevertheless retained an older compatibility path that reconstructed the same
view through separate `/api/config`, `/api/hosts`, `/api/roster`, and
`/api/snapshots` requests when `/api/control` was absent or malformed.

That path could not prove one cross-endpoint snapshot, duplicated validation
and request payload, and made an incompatible server look temporarily usable
instead of failing closed. It had no supported mixed-version deployment
contract and consumed scarce release-asset budget.

## Current state

The browser accepts only the authenticated `agency.dashboard.control.v1`
response. A 404, network failure, missing schema, wrong schema, abort, or stale
refresh cannot trigger legacy endpoint requests. Non-cancellation failures
retain the last-good rendered state and surface the correlated failure through
the existing dashboard boundary.

The July 27 removal saved 1,436 production bytes; its reported 257,620-byte
total and 5,547-byte headroom are historical. The legacy fallback remains absent.
September 7 review reproduced eight request-ID losses on invalid control schema
or JSON across both refresh paths. Moving schema validation into the existing
API boundary repairs them without restoring fallback. Twenty direct regression
cases now pass, including HTTP/network failures and quiet cancellation/lifecycle
races. All 224 UI tests pass at current coverage floors. The ten assets total
386,965 bytes, 107 below the unchanged current 378-KiB strict ceiling; this
repair removes 74 bytes. Browser proof and isolated acceptance remain pending.

## Approach

Treat the dashboard and server asset set as one release unit. Require the
current control schema, preserve last-good state on incompatibility, and test
the absence of every legacy request explicitly. Do not raise the asset ceiling
or retain silent compatibility that cannot preserve snapshot identity.

## Dependencies

ADR-0029 keeps the local dashboard authenticated and bounded. ADR-0032 owns its
polling transport. ADR-0095 requires complete revision-bound collection truth.
AR-170 and AR-172 provide the exact response and Store/configuration identities
that the current control envelope carries.

The existing pre-tracker exemption applies; no duplicate tracker is created.
Only obsolete criterion 6 follows ADR-0105; its original wording is retained.

## Acceptance

- [x] `/api/control` must return `agency.dashboard.control.v1`.
- [x] Missing, malformed, wrong-schema, network, and stale responses retain
  last-good state and never fan out to legacy endpoints.
- [x] Abort and lifecycle races remain cancellations rather than visible
  compatibility failures.
- [x] Browser tests cover 404 and wrong-schema retention and assert zero legacy
  endpoint calls.
- [x] The fixed dashboard release-asset ceiling passes without being raised.
- [ ] Focused control regressions, full UI/current coverage floors, current
  asset gate, named production spine, private loaded-browser proof, metadata,
  policy, worklog, strict docs/tracker, Ruff and diff checks pass; exhaustive
  integration remains optional under ADR-0105.

## Preserved original criterion

6. The final repository release gate passes at the implementation commit.

## Implementation evidence

The browser interaction suite passes 105 tests, the release-packaging suite
passes 121 tests, and `git diff --check` passes. The removed path accounts for
1,436 bytes; total dashboard headroom is 5,547 bytes under the strict ceiling.
Those are the historical implementation measurements. The current
[September 7 receipt](acceptance/evidence/AR-175-control-boundary-20260907.md)
retains the eight reproduced failures, twenty-case repair and unchanged current
asset ceiling. No new native host or Windows evidence is claimed.
