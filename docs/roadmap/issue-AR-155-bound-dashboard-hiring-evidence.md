---
title: "AR-155: Bound dashboard hiring evidence delivery"
status: done
category: roadmap
created: 2026-07-26
updated: 2026-09-07
tags: [dashboard, workforce, availability, pagination, performance]
related:
  - docs/roadmap/acceptance/issue-AR-155.md
  - docs/roadmap/acceptance/evidence/AR-155-hiring-evidence-20260907.md
  - docs/decisions/0105-bound-delivery-to-live-demo-checkpoints.md
  - docs/decisions/0220-measure-dashboard-coverage-over-production-modules.md
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

Current main 434175f0 contains the 6a3bdaa repair. Collection SQL projects only
fixed lifecycle fields, never the five evidence columns; Store and HTTP enforce
the 200-row/1 MiB collection contract. Exact-case lookup keeps all five documents
without that collection cap. The UI loads exact evidence on explicit inspection
and rejects stale or mismatched results. No code/test edit is needed.

Fresh bounded-collection/response tests pass four; complete workforce lifecycle
passes 25; full UI passes 188/current production floors. Unchanged Python/source
receipts supply 274 dashboard and 1085-spine/three-skip results as explicit reuse.
All five isolated criteria satisfy at 6ed24943 on September 7. The initial
criterion-3 verifier failure is preserved at a3e00bd5; its one unchanged-candidate
retry supplies the missing verdict. PR #707 carries completion. This is not
constant-memory whole-store work:
revision construction still reads collection metadata, not document bodies.

ADR-0105 supersedes mandatory exhaustive diagnostics. Only criterion 5 is
reconciled to Store/dashboard checks, UI production coverage and the named
warning-strict spine; ADR-0220 retains 95/86/93 floors. Original wording is
preserved below; the first four criteria are unchanged.

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

- [x] Hiring collection rows contain no full evidence documents.
- [x] A maximum-size 200-row collection remains within an explicit response-byte budget.
- [x] Exact-case lookup retains every governed evidence document without truncation.
- [x] The UI fetches exact evidence only on explicit inspection and rejects stale responses.
- [x] Store, dashboard, UI production coverage, and the named warning-strict production spine pass.

## Historical fifth criterion

Original wording: "Store, dashboard, UI, coverage, and full warning-strict release
gates pass." ADR-0105 governs bounded verification; this package does not claim
an exhaustive corpus, aggregate Python coverage or interpreter-matrix pass.

## Historical implementation evidence

Commit `6a3bdaa` projects fixed-field collection summaries with
`evidence_included=false`, retains every governed document only behind exact
case lookup with `evidence_included=true`, and binds explicit inspection to the
active lifecycle and selected case. Store and HTTP enforce the unchanged 1 MiB
hiring-collection response budget; invariant failures return a generic 500 and
do not expose private payloads. The shared focused package passed 168 Python
tests with 3 skips, four post-review regressions, and 101 dashboard UI tests.
Full current-artifact and warning-strict evidence remain.
