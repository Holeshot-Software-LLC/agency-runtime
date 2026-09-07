---
title: "AR-150 acceptance verification record"
status: active
category: roadmap
created: 2026-09-07
updated: 2026-09-07
tags: [acceptance, verification, dashboard, concurrency]
related:
  - docs/roadmap/issue-AR-150-coordinate-dashboard-refresh-epochs.md
  - docs/roadmap/acceptance/evidence/AR-150-refresh-epochs-20260907.md
supersedes: []
superseded_by: null
type: acceptance-verification
issue_id: AR-150
candidate_commit: 57c225c189e39eae347129eb07e2a156e110b56b
evidence_cutoff: 2026-09-07
tracker_url: null
---

# AR-150 acceptance verification record

## Builder evidence

| Criterion | Kind | Artifact | Observed | Source |
|---|---|---|---|---|
| 1 | file | View requests invalidate old scopes and require the captured shared epoch and controller before committing | 2026-09-07 | agency_runtime/dashboard/dashboard-live.js:951-1012 |
| 1 | file | Workforce refresh uses the same epoch/controller checks, including supplied abort signals | 2026-09-07 | agency_runtime/dashboard/dashboard-live.js:2353-2387 |
| 1 | test | Newer view intent wins pending control/full and cross-view remediation responses | 2026-09-07 | tests/dashboard_ui.test.mjs:4636-4784 |
| 1 | command-output | The complete 172-test UI suite passes, including deferred cross-scope cases | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-150-refresh-epochs-20260907.md#current-verification |
| 2 | file | Control/full refresh checks the captured commit generation before applying state; starting full refresh cancels view requests | 2026-09-07 | agency_runtime/dashboard/dashboard-live.js:2076-2195 |
| 2 | test | Both exact-first and operational-first response orders retain the newest compatible roster state | 2026-09-07 | tests/dashboard_ui.test.mjs:6538-6609 |
| 2 | test | Initial and periodic control refresh bind panels to one complete snapshot | 2026-09-07 | tests/dashboard_ui.test.mjs:4350-4444 |
| 2 | command-output | Current UI and server integration checks pass against unchanged source | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-150-refresh-epochs-20260907.md#current-verification |
| 3 | test | Abort/stale generations and invalid control snapshots preserve prior state | 2026-09-07 | tests/dashboard_ui.test.mjs:4277-4468 |
| 3 | test | Workforce and hiring preserve last-good data and expose source-specific stale state | 2026-09-07 | tests/dashboard_ui.test.mjs:6197-6269 |
| 3 | file | Focus, selection and open disclosures are preserved around rendering | 2026-09-07 | agency_runtime/dashboard/dashboard-core.js:440-490 |
| 3 | command-output | Same-byte installed-wheel proof retains focus/selection/disclosures during real polling and recovers from visible stale failure | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-150-refresh-epochs-20260907.md#unchanged-installed-wheel-evidence |
| 3 | command-output | Exact browser failure and interaction results are preserved in the repaired receipt | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-138-repaired-dashboard-20260907.md#browser-evidence |
| 4 | command-output | Fresh UI run passes 172 with 96.93/86.58/95.71 coverage; fresh dashboard server/auth/transaction run passes 180 | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-150-refresh-epochs-20260907.md#current-verification |
| 4 | file | The current configured UI gate includes all production scripts and requires 95/86/93 | 2026-09-07 | .github/workflows/ci.yml:279-285 |
| 4 | test | Dashboard workforce and hiring API integration binds lifecycle state to revisions | 2026-09-07 | tests/test_dashboard.py:888-935 |
| 4 | test | Dashboard bearer admission rejects unsafe tokens and accepts exact authorized tokens | 2026-09-07 | tests/test_dashboard_auth_boundary_regression.py:21-48 |

## Verification

No verdicts supplied yet; the isolated runner owns this table.

| Criterion | Verdict | Verifier run | Evidence digest | Observed | Reason |
|---|---|---|---|---|---|
| 1 | satisfied | `AR-150.1-20260907-956ac5bd` | `6f9f8782acb8fe500544faa3d52df941a7969b5f5ef5d7f709ff54102cc01cb7` | 2026-09-07 | dashboard-live.js shows shared epoch and controller guards, including workforce commits; dashboard_ui.test.mjs demonstrates deferred control and full responses preserving newer filters, and the cited verification receipt reports 172 passing tests. |
| 2 | absent | `AR-150.2-20260907-a6c51b1f` | `a8e56a3aac4cea784e6fad7fc62224eac65d2945ba5a69e07d4f1db1518d3243` | 2026-09-07 | dashboard-live.js shows generation guards, but the cited tests cover roster intent ordering and uncontested refreshes, without demonstrating that inverse refresh response order cannot combine incompatible revisions. |
| 3 | satisfied | `AR-150.3-20260907-dba40e05` | `59dfcd54d52889aa78090f188f35559a136e2c3817f141a9f6bddb4da3552378` | 2026-09-07 | The dashboard_ui tests demonstrate cancellation and last-good stale handling, dashboard-core.js preserves interaction state, and the browser receipt records focus retention, visible stale failure, and recovery during real polling. |
| 4 | satisfied | `AR-150.4-20260907-4601aec7` | `9baa9f1cf0ac804c4551f847da3fcc34e41baf8e9364315bdbef2f20417cbf1e` | 2026-09-07 | The current-verification receipt records 172 UI tests passing at 96.93/86.58/95.71, exceeding ci.yml’s exact 95/86/93 floors, and 180 server integration tests passing without failures or skips. |
