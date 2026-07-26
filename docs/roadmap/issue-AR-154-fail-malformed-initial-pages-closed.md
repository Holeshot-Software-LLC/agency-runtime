---
title: "AR-154: Fail malformed initial dashboard pages closed"
status: open
category: roadmap
created: 2026-07-26
updated: 2026-07-26
tags: [dashboard, pagination, validation, traceability]
related:
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

Later pages reject an omitted cursor, but equivalent first-page corruption is
not covered and takes a permissive path.

## Approach

Require a bounded next cursor whenever any page is truncated and require the
initial revision needed for multi-page consistency. Preserve last-good state and
surface the existing bounded stale/error projection on failure.

## Dependencies

AR-137, AR-146, and ADR-0095 define the complete collection and cursor contract.

## Acceptance

- An initial truncated page without a next cursor is rejected.
- Multi-page data without an initial revision is rejected before composition.
- Malformed pages cannot replace last-good dashboard state.
- Cursor, activity, observation, and exact dashboard UI coverage tests pass.
