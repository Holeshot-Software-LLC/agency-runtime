---
title: "AR-153: Complete and bound worker-detail evidence"
status: open
category: roadmap
created: 2026-07-26
updated: 2026-09-07
tags: [dashboard, workforce, sqlite, traceability]
related:
  - docs/decisions/0027-authoritative-runtime-evidence-traces.md
  - docs/decisions/0095-complete-paginated-dashboard-collections.md
  - docs/decisions/0105-bound-delivery-to-live-demo-checkpoints.md
  - docs/roadmap/issue-AR-137-complete-dashboard-collections.md
  - docs/roadmap/issue-AR-404-evidence-led-backlog-completion.md
  - docs/roadmap/acceptance/evidence/AR-153-worker-detail-20260907.md
  - docs/roadmap/acceptance/issue-AR-153.md
  - docs/worklog/README.md
  - agency_runtime/core/store/workforce.py
supersedes: []
superseded_by: null
type: issue
epic: dashboard
issue_id: AR-153
priority: p1
tracker_url: null
depends_on: []
blocks: [AR-170, AR-171]
---

# AR-153: Complete and bound worker-detail evidence

## Problem

Worker detail selects the globally newest hiring cases before filtering them for
the requested worker. Older matching evidence disappears when enough unrelated
cases are newer, while lineage is queried without the public evidence bound.

## Current state

September 7 review confirms 6a3bdaa's repair remains implemented. Worker identity
predicates precede the hiring-case LIMIT. Lineage rows and all evidence pages
are limited, with independent exact totals and truncation flags from one Store
read transaction. The HTTP detail projection omits retained history documents,
caps evidence at 200 rows per collection and enforces a 2 MiB response budget.
The UI renders the loaded records and distinguishes loaded counts from totals.

Fresh verification: six focused worker-detail Store/HTTP regressions pass in
2.71s; complete workforce-lifecycle module passes 25 in 8.08s; complete UI passes
176 in 223.89ms at unchanged 95/86/93 floors (96.93/86.70/95.71 observed).
Product/tests/scripts equal AR-151 candidate 99e05d1f, so its 274-pass dashboard
suite and 1085-pass/three-skip named spine are exact-byte reuse, not new runs.
No runtime or test change is needed; isolated acceptance remains.

ADR-0105 supersedes the old mandatory exhaustive-corpus requirement. Criterion
4 now names the focused Store/dashboard suites and warning-strict production
spine. The historical wording remains below; no full-corpus success is claimed.

## Approach

Filter by worker identity in SQL before applying the evidence limit. Bound or
page lineage under an explicit public contract, expose truncation truthfully,
and render only evidence the response actually contains.

## Dependencies

AR-137 provides bounded collection contracts; AR-142 and ADR-0027 require exact
evidence attribution.

## Acceptance

- [ ] More than the limit of newer unrelated cases cannot hide matching worker evidence.
- [ ] Lineage work and response size are explicitly bounded or paginated.
- [ ] Counts, records, and truncation indicators agree from SQL through UI.
- [ ] Focused Store and dashboard suites and the named warning-strict production spine pass.

## Historical fourth criterion

Original wording: "Focused Store, dashboard, and full warning-strict suites
pass." ADR-0105 makes the complete corpus, four-shard coverage and interpreter
matrix optional owner-requested diagnostics rather than completion gates.
The first three criteria are unchanged. This is explicit policy reconciliation,
not a claim that the old exhaustive run passed.

## Implementation evidence

Commit `6a3bdaa` filters hiring cases by worker identity before applying the
evidence limit, bounds lineage and worker-detail delivery, and carries exact
total/truncation metadata through Store, HTTP, and UI. Response-size invariant
failures remain server-side and return a generic error rather than leaking
private evidence. The shared focused package passed 168 Python tests with 3
skips, four post-review regressions, and 101 dashboard UI tests. Full
warning-strict and artifact evidence remain.
