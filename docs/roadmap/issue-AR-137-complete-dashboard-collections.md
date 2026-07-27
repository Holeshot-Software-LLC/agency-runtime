---
title: "AR-137: Make dashboard collections complete and paginated"
status: open
category: roadmap
created: 2026-07-26
updated: 2026-07-27
tags: [dashboard, workforce, pagination, ui, truth]
related:
  - docs/decisions/0095-complete-paginated-dashboard-collections.md
  - docs/roadmap/issue-AR-146-repair-dashboard-collection-cursor-validation.md
  - agency_runtime/server/dashboard.py
  - agency_runtime/dashboard/dashboard-live.js
supersedes: []
superseded_by: null
type: issue
epic: dashboard
issue_id: AR-137
priority: p0
tracker_url: null
depends_on: []
blocks:
  - AR-146
  - AR-155
  - AR-172
---

# AR-137: Make dashboard collections complete and paginated

## Problem

The workforce UI requests 1,000 rows, the server silently caps generic queries
at 200, and the bundled roster already contains 263 manifest agents. Counts and
filtered lists can therefore look complete while hiding valid workers. Similar
fixed caps affect hiring and roster review views.

## Current state

Responses provide no cursor or truncation marker, and some UI totals are
calculated from the returned page. Worker detail is also constrained by an
uncoordinated 100-row filtered view.

## Approach

Expose stable cursor pagination, explicit `truncated` and `next_cursor` fields,
and independently calculated total/facet counts for every collection. Teach
the UI to page or deliberately virtualize without presenting page size as the
population size.

## Dependencies

ADR-0095 defines collection completeness. AR-138 owns asynchronous UI state.

## Acceptance

- Workforces of 263, 1,001, and filtered subsets expose exact totals and all
  rows through stable pagination.
- Hiring, roster, activity, and workforce views declare truncation consistently.
- Paging remains deterministic under concurrent inserts using documented
  cursor semantics.
- UI labels distinguish page count, filtered total, and global total.

## Implementation evidence

Workforce, hiring, roster snapshots, candidate reviews, and activity now expose
bounded keyset cursors, exact page/filtered/global totals, collection revisions,
and declared live-cursor semantics. The browser drains complete control
collections deliberately and renders totals separately from the current page;
worker detail no longer depends on a truncated filtered view. Dashboard server
tests pass 137 with 3 skips and browser interaction tests pass 82. Explicit
263- and 1,001-worker regressions drain every page with exact global and
filtered facets. A committed inter-page insertion appears exactly once in
stable key order, changes the collection revision, and preserves the declared
live-keyset-after-exclusive contract. Local acceptance is satisfied; the item
remains open only because tracker creation and closure are unauthorized
outward actions.

Post-implementation traceability coverage found that the cursor validator used
a literal backslash-Z suffix, so generated activity cursors could not be
consumed. AR-146 corrects the anchor and adds canonical round-trip, hostile
cursor, and handler-to-Store keyset tests. Its focused server suite passes 29
tests and the existing cursor/activity regressions pass 12.
