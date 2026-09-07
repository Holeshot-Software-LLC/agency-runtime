---
title: "AR-154: Fail malformed initial dashboard pages closed"
status: done
category: roadmap
created: 2026-07-26
updated: 2026-09-07
tags: [dashboard, pagination, validation, traceability]
related:
  - docs/roadmap/acceptance/issue-AR-154.md
  - docs/roadmap/acceptance/evidence/AR-154-initial-page-validation-20260907.md
  - docs/decisions/0220-measure-dashboard-coverage-over-production-modules.md
  - docs/decisions/0095-complete-paginated-dashboard-collections.md
  - docs/roadmap/issue-AR-137-complete-dashboard-collections.md
  - docs/roadmap/issue-AR-146-repair-dashboard-collection-cursor-validation.md
  - agency_runtime/dashboard/dashboard-live.js
supersedes: []
superseded_by: null
type: issue
epic: dashboard
issue_id: AR-154
priority: p1
tracker_url: null
depends_on: []
blocks: []
---

# AR-154: Fail malformed initial dashboard pages closed

## Problem

The browser can treat an initial `truncated: true` collection without a
`next_cursor` as complete. It also skips cross-page revision validation when the
initial revision is absent, allowing malformed evidence to appear authoritative.

## Current state

The original defect is repaired in current main 8b36ea28. Initial and later pages
share schema, cursor and revision validation; the initial page is validated
before any row copying or continuation request. The original helper regression
proves rejection without a request. No runtime change is needed.

Twelve new direct refresh tests cover missing initial cursor/revision in roster,
snapshots and reviews through both full/manual and periodic controllers. Valid
last-good state is first loaded, then malformed replacement data is rejected;
configuration, hosts, collection data and revisions remain unchanged and stale
state is visible. All twelve pass. Focused cursor/activity/observation tests pass
13; complete UI passes 188 at current production coverage floors. Unchanged
Python/source receipts are explicitly reused. All four original criteria satisfy
against e1c3069c on September 7; exact run IDs/digests are in the acceptance record.
PR #706 carries this completion; no duplicate legacy tracker is created.

## Approach

Verify the existing bounded cursor/revision admission and last-good-state
preservation with direct refresh regressions. Retain the original criteria;
obtain isolated verdicts and publish one bounded PR before moving to AR-155.

## Dependencies

AR-137, AR-146, and ADR-0095 define the complete collection and cursor contract.

## Acceptance

- [x] An initial truncated page without a next cursor is rejected.
- [x] Multi-page data without an initial revision is rejected before composition.
- [x] Malformed pages cannot replace last-good dashboard state.
- [x] Cursor, activity, observation, and exact dashboard UI coverage tests pass.

## Historical implementation evidence

Commit `6a3bdaa` validates exact initial-page schemas, requires a cursor for
every truncated page, and requires the revision needed to compose multi-page
state. Malformed initial and later pages now preserve last-good state and expose
the bounded stale/error projection. The shared focused package passed 168
Python tests with 3 skips, four post-review regressions, and 101 dashboard UI
tests. Final current-artifact and aggregate release evidence remain.
