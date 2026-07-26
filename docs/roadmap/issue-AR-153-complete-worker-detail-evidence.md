---
title: "AR-153: Complete and bound worker-detail evidence"
status: open
category: roadmap
created: 2026-07-26
updated: 2026-07-26
tags: [dashboard, workforce, sqlite, traceability]
related:
  - docs/decisions/0027-authoritative-runtime-evidence-traces.md
  - docs/decisions/0095-complete-paginated-dashboard-collections.md
  - docs/roadmap/issue-AR-137-complete-dashboard-collections.md
  - agency_runtime/core/store/workforce.py
supersedes: []
superseded_by: null
type: issue
epic: dashboard
issue_id: AR-153
priority: p1
tracker_url: null
depends_on: []
blocks: []
---

# AR-153: Complete and bound worker-detail evidence

## Problem

Worker detail selects the globally newest hiring cases before filtering them for
the requested worker. Older matching evidence disappears when enough unrelated
cases are newer, while lineage is queried without the public evidence bound.

## Current state

The UI promises lineage and hiring evidence but may receive an incomplete hiring
projection and an unbounded lineage result; it currently emphasizes counts over
the bounded records.

## Approach

Filter by worker identity in SQL before applying the evidence limit. Bound or
page lineage under an explicit public contract, expose truncation truthfully,
and render only evidence the response actually contains.

## Dependencies

AR-137 provides bounded collection contracts; AR-142 and ADR-0027 require exact
evidence attribution.

## Acceptance

- More than the limit of newer unrelated cases cannot hide matching worker evidence.
- Lineage work and response size are explicitly bounded or paginated.
- Counts, records, and truncation indicators agree from SQL through UI.
- Focused Store, dashboard, and full warning-strict suites pass.

## Implementation evidence

Commit `6a3bdaa` filters hiring cases by worker identity before applying the
evidence limit, bounds lineage and worker-detail delivery, and carries exact
total/truncation metadata through Store, HTTP, and UI. Response-size invariant
failures remain server-side and return a generic error rather than leaking
private evidence. The shared focused package passed 168 Python tests with 3
skips, four post-review regressions, and 101 dashboard UI tests. Full
warning-strict and artifact evidence remain.
