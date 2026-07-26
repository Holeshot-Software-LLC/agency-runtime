---
title: "AR-151: Align Route Lab host eligibility with the server"
status: open
category: roadmap
created: 2026-07-26
updated: 2026-07-26
tags: [dashboard, routing, hosts, traceability]
related:
  - docs/decisions/0095-complete-paginated-dashboard-collections.md
  - docs/roadmap/issue-AR-137-complete-dashboard-collections.md
  - agency_runtime/dashboard/dashboard-render.js
  - agency_runtime/server/dashboard.py
supersedes: []
superseded_by: null
type: issue
epic: dashboard
issue_id: AR-151
priority: p1
tracker_url: null
depends_on: []
blocks: []
---

# AR-151: Align Route Lab host eligibility with the server

## Problem

The browser keeps the first duplicate host and can enable Route Lab while the
server classifies duplicate or oversized inventories as ambiguous and rejects
the same request. The UI can therefore advertise an action it cannot perform.

## Current state

Host cards and server validation each derive eligibility independently. Existing
tests even preserve the browser's first-duplicate behavior.

## Approach

Use a server-projected eligibility result or reproduce the exact bounded
duplicate/size rejection in the browser. Keep the POST boundary authoritative
and render an explicit unavailable reason before submission.

## Dependencies

AR-137 and ADR-0095 govern complete bounded host collections.

## Acceptance

- Duplicate and oversized host inventories cannot enable Route Lab.
- Browser eligibility and the authoritative POST handler agree on valid hosts.
- The UI renders an explicit bounded reason for ambiguous inventory.
- UI-to-POST contract and full dashboard suites pass.

## Implementation evidence

Commit `6a3bdaa` makes Route Lab derive eligibility from the complete bounded
host inventory and disables submission for duplicate or oversized evidence
with an explicit unavailable reason; the POST boundary remains authoritative.
Client/server contract regressions cover valid, duplicate, and oversized host
sets. The shared focused package passed 168 Python tests with 3 skips, four
post-review regressions, and 101 dashboard UI tests. Installed-browser and full
current-head evidence remain.
