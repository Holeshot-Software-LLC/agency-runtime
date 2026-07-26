---
title: "Worklog: Restore coverage contracts and cursor paging"
status: active
category: worklog
created: 2026-07-26
updated: 2026-07-26
tags: [release, coverage, dashboard, pagination, authority]
related:
  - docs/roadmap/issue-AR-137-complete-dashboard-collections.md
  - docs/roadmap/issue-AR-145-restore-python-release-coverage.md
  - docs/roadmap/issue-AR-146-repair-dashboard-collection-cursor-validation.md
supersedes: []
superseded_by: null
type: worklog
commit: c3ffe6a7fbe2d1797cef55022b4a6b65abac7d62
short: c3ffe6a
date: 2026-07-26
pr: null
related_issues:
  - docs/roadmap/issue-AR-137-complete-dashboard-collections.md
  - docs/roadmap/issue-AR-145-restore-python-release-coverage.md
  - docs/roadmap/issue-AR-146-repair-dashboard-collection-cursor-validation.md
---

# Worklog: Restore coverage contracts and cursor paging

## Purpose

Repair the exact Python release-coverage contract and a traceability defect
that made every generated dashboard activity cursor unusable.

## Approach

Replaced scheduler-dependent assertions with authoritative event
synchronization, separated deterministic report-contract tests from real
wall-clock gates, and added behavioral coverage for finalization, maintenance,
observed SQLite, MCP, and dashboard collection boundaries. Corrected the
dashboard cursor regex end anchor and locked its complete handler-to-Store
round-trip.

## Challenges encountered

The first exact coverage run took 57m35s and exposed four failures plus a 96.66
percent aggregate result. Focused diagnosis separated three test-contract
problems from the real cursor bug. Concurrent coverage processes also collide
on the default data file, so focused measurements used unique files.

## Decisions and alternatives

Coverage thresholds and exclusions remain unchanged. Production observation
ordering and preflight lease budgets remain unchanged because their failures
were test synchronization defects. Cursor validation changed because its own
generated values proved the production regex wrong.

## Verification

- Integrated repaired package: 73 passed.
- Matched Store/MCP package: 245 passed; 177 more statements and 38 fewer
  partial branches.
- Dashboard server package: 29 passed; 87 more statements covered.
- Existing cursor/activity/observation regressions: 12 passed.
- Ruff, format, documentation, and diff checks: passed.

## Follow-ups

AR-145 still requires the exact aggregate 97 percent coverage rerun and the
separate uninstrumented performance suite. Fresh installed browser QA remains
governed by AR-138 and genuine operator presence by AR-143.
