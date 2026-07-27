---
title: "AR-175: Retire the non-atomic dashboard control fallback"
status: in_progress
category: roadmap
created: 2026-07-27
updated: 2026-07-27
tags: [dashboard, traceability, performance, compatibility, security]
related:
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

Removing the unreachable path saves 1,436 production bytes. Together with the
separate dead-markup and CSS cleanup, the ten shipped dashboard assets total
257,620 bytes, 5,547 bytes below the unchanged strict ceiling.

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

Tracker creation remains pending explicit outward-write authorization.

## Acceptance

- [x] `/api/control` must return `agency.dashboard.control.v1`.
- [x] Missing, malformed, wrong-schema, network, and stale responses retain
  last-good state and never fan out to legacy endpoints.
- [x] Abort and lifecycle races remain cancellations rather than visible
  compatibility failures.
- [x] Browser tests cover 404 and wrong-schema retention and assert zero legacy
  endpoint calls.
- [x] The fixed dashboard release-asset ceiling passes without being raised.
- [ ] The final repository release gate passes at the implementation commit.

## Implementation evidence

The browser interaction suite passes 105 tests, the release-packaging suite
passes 121 tests, and `git diff --check` passes. The removed path accounts for
1,436 bytes; total dashboard headroom is 5,547 bytes under the strict ceiling.
Final aggregate evidence is recorded only after the implementation commit's
full gate.
