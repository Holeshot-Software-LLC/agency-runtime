---
title: "AR-172: Make roster pages snapshot-consistent"
status: in_progress
category: roadmap
created: 2026-07-27
updated: 2026-07-27
tags: [roster, sqlite, dashboard, pagination, performance, traceability]
related:
  - docs/decisions/0012-canonical-sqlite-audit-store.md
  - docs/decisions/0046-config-backed-agent-activation-policy.md
  - docs/decisions/0095-complete-paginated-dashboard-collections.md
  - docs/roadmap/issue-AR-137-complete-dashboard-collections.md
  - docs/roadmap/issue-AR-146-repair-dashboard-collection-cursor-validation.md
  - docs/roadmap/issue-AR-175-retire-dashboard-control-fallback.md
  - agency_runtime/core/store/roster.py
  - agency_runtime/dashboard/dashboard-live.js
  - agency_runtime/server/dashboard.py
  - agency_runtime/server/http.py
  - tests/test_dashboard.py
  - tests/test_roster_snapshot_generation.py
  - tests/test_senior_audit_hardening.py
  - tests/dashboard_ui.test.mjs
supersedes: []
superseded_by: null
type: issue
epic: operations
issue_id: AR-172
priority: p1
tracker_url: null
depends_on: [AR-137, AR-146]
blocks: [AR-175]
---

# AR-172: Make roster pages snapshot-consistent

## Problem

The public `/roster` handler read its page and total through separate Store
connections, while `get_enabled_roster` materialized the eligible tail before
applying the HTTP page bound. A concurrent activation could pair one generation
with another generation's count, and a large roster caused unnecessary decode
and Python filtering work.

Dashboard roster rows also apply the configuration-backed disabled-agent set,
but paging continuity checked only the Store roster generation. An operator
configuration change between pages could keep the Store revision unchanged and
silently mix enabled and disabled projections in one browser collection.

Finally, `/api/control` captured its roster page and operational roster in two
Store transactions without comparing their generations. A concurrent
activation could publish generation A cards and generation B operational facts
under one authoritative-looking control revision even when no browser paging
was necessary.

## Current state

The public handler uses one Store snapshot that reads roster generation, exact
eligible total, and `limit + 1` rows inside one SQLite read transaction. SQL
applies the bounded disabled-agent set and page cursor before decoding. The
dashboard exposes the exact configuration revision on its initial control page
and requires the same revision on every primary, exact-lookup, and operational
roster page in addition to the Store roster revision.

The control handler performs a bounded recapture and publishes only when the UI
roster and operational projection report the same exact Store generation. If a
stable pair cannot be obtained inside the bound, the request fails closed.

## Approach

Freeze both components of effective roster identity at their owning boundary:
SQLite owns active definitions and generation, while the typed configuration
owns reversible activation. Apply stable filtering and `LIMIT` in parameterized
SQL, return count and rows from the same read transaction, and make the browser
reject any page whose Store or configuration revision differs from the first
page or enclosing control snapshot.

## Dependencies

ADR-0012 owns authoritative SQLite snapshots. ADR-0046 separates reversible
availability from governed roster state. ADR-0095 requires explicit cursor and
revision semantics for complete dashboard collections.

Tracker creation remains pending explicit outward-write authorization.

## Acceptance

- [x] Public roster generation, total, and rows come from one read snapshot.
- [x] Disabled filtering, cursor filtering, and `limit + 1` happen in SQL with
  bounded parameters; protected coordinators remain enabled.
- [x] A deterministic concurrent writer cannot mix roster generations.
- [x] Dashboard roster and operational pages bind both Store generation and
  configuration revision across the current control and collection paths.
- [x] A configuration change during paging retains last-good UI state and fails
  the refresh closed.
- [x] One control response never combines UI and operational roster generations;
  a deterministic mismatch is recaptured once and persistent churn fails closed.
- [ ] The final repository release gate passes at the implementation commit.

## Implementation evidence

Focused Store tests inspect the executed SQL and interleave a second Store
writer after the reader establishes its snapshot. HTTP and browser tests cover
the unchanged public envelope, initial control revision, subsequent-page
continuity, exact lookup, and operational paging. Final aggregate evidence is
recorded only after the implementation commit's full gate.
