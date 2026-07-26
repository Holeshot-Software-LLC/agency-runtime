---
title: "AR-155: Bound dashboard hiring evidence delivery"
status: open
category: roadmap
created: 2026-07-26
updated: 2026-07-26
tags: [dashboard, workforce, availability, pagination, performance]
related:
  - docs/decisions/0095-complete-paginated-dashboard-collections.md
  - docs/roadmap/issue-AR-137-complete-dashboard-collections.md
  - docs/roadmap/issue-AR-153-complete-worker-detail-evidence.md
  - agency_runtime/core/store/workforce.py
  - agency_runtime/server/dashboard.py
  - agency_runtime/dashboard/dashboard-live.js
supersedes: []
superseded_by: null
type: issue
epic: dashboard
issue_id: AR-155
priority: p1
tracker_url: null
depends_on:
  - AR-137
blocks: []
---

# AR-155: Bound dashboard hiring evidence delivery

## Problem

The paginated hiring collection includes five independently bounded evidence
documents for every case. A legal 200-row page can therefore exceed 200 MiB,
and the browser eagerly follows as many as 100 pages into one retained array.
An ordinary authenticated Workforce refresh can exhaust service or browser
memory even though the row count and each individual document are bounded.

## Current state

Each hiring evidence document may contain 256 KiB. The collection Store query
selects and decodes all five documents, the dashboard serializes the complete
page in memory, and the UI drains every page before rendering. The existing
exact-case API already provides a suitable boundary for full evidence but the
browser does not use it on demand.

## Approach

Project fixed-field hiring summaries in collection queries and reserve the full
documents for the exact `case_id` endpoint. Render summary cards first, then
load one exact case only after explicit operator inspection. Bind that request
to the current dashboard lifecycle and selected case so stale evidence cannot
commit after a newer intent.

## Dependencies

AR-137 and ADR-0095 define complete bounded collections. AR-153 establishes the
same summary-versus-exact-evidence distinction for worker detail.

## Acceptance

- Hiring collection rows contain no full evidence documents.
- A maximum-size 200-row collection remains within an explicit response-byte budget.
- Exact-case lookup retains every governed evidence document without truncation.
- The UI fetches exact evidence only on explicit inspection and rejects stale responses.
- Store, dashboard, UI, coverage, and full warning-strict release gates pass.
