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
  - docs/roadmap/acceptance/evidence/AR-150-inverse-order-proof-20260907.md
supersedes: []
superseded_by: null
type: acceptance-verification
issue_id: AR-150
candidate_commit: ae71761f83eb83c7f258336acc76cc32044009a2
evidence_cutoff: 2026-09-07
tracker_url: null
---

# AR-150 acceptance verification record

## Builder evidence

| Criterion | Kind | Artifact | Observed | Source |
|---|---|---|---|---|
| 1 | file | View requests invalidate old scopes and require the captured shared epoch and controller before committing | 2026-09-07 | agency_runtime/dashboard/dashboard-live.js:951-1012 |
| 1 | file | Workforce refresh uses the same epoch/controller checks, including supplied abort signals | 2026-09-07 | agency_runtime/dashboard/dashboard-live.js:2353-2387 |
| 1 | test | Newer view intent wins pending control/full and cross-view remediation responses | 2026-09-07 | tests/dashboard_ui.test.mjs:4722-4870 |
| 1 | test | Both workforce/full directions reject obsolete responses even after abort | 2026-09-07 | tests/dashboard_ui.test.mjs:496-579 |
| 1 | command-output | Four direct overlap cases and the complete 176-test UI suite pass | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-150-inverse-order-proof-20260907.md#current-checks |
| 2 | file | Control/full refresh checks the captured commit generation before applying state; starting full refresh cancels view requests | 2026-09-07 | agency_runtime/dashboard/dashboard-live.js:2076-2195 |
| 2 | test | Workforce then full and full then workforce each run older-first and newer-first responses and assert all resulting collection and snapshot revisions | 2026-09-07 | tests/dashboard_ui.test.mjs:496-579 |
| 2 | command-output | The direct four-case matrix deliberately delivers aborted responses and checks one compatible revision set | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-150-inverse-order-proof-20260907.md#direct-inverse-order-matrix |
| 2 | command-output | All four direct inverse-order tests and full UI coverage pass | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-150-inverse-order-proof-20260907.md#current-checks |
| 3 | test | Abort/stale generations and invalid control snapshots preserve prior state | 2026-09-07 | tests/dashboard_ui.test.mjs:4363-4554 |
| 3 | test | Workforce and hiring preserve last-good data and expose source-specific stale state | 2026-09-07 | tests/dashboard_ui.test.mjs:6283-6355 |
| 3 | file | Focus, selection and open disclosures are preserved around rendering | 2026-09-07 | agency_runtime/dashboard/dashboard-core.js:440-490 |
| 3 | command-output | Same-byte installed-wheel proof retains focus/selection/disclosures during real polling and recovers from visible stale failure | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-150-refresh-epochs-20260907.md#unchanged-installed-wheel-evidence |
| 3 | command-output | Exact browser failure and interaction results are preserved in the repaired receipt | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-138-repaired-dashboard-20260907.md#browser-evidence |
| 4 | command-output | Complete UI passes 176 with 96.93/86.70/95.71 coverage; server source and tests unchanged from this package's 180-pass integration run | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-150-inverse-order-proof-20260907.md#current-checks |
| 4 | command-output | Exact dashboard server/auth/transaction command and 180-pass result | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-150-refresh-epochs-20260907.md#current-verification |
| 4 | file | The current configured UI gate includes all production scripts and requires 95/86/93 | 2026-09-07 | .github/workflows/ci.yml:279-285 |
| 4 | test | Dashboard workforce and hiring API integration binds lifecycle state to revisions | 2026-09-07 | tests/test_dashboard.py:888-935 |
| 4 | test | Dashboard bearer admission rejects unsafe tokens and accepts exact authorized tokens | 2026-09-07 | tests/test_dashboard_auth_boundary_regression.py:21-48 |

## Verification

First-candidate verdicts (three satisfied, criterion 2 absent) are preserved at
4e820ff4. This second candidate supplies direct inverse-order evidence; the
isolated runner owns the new table below. No prior verdict is carried forward.

| Criterion | Verdict | Verifier run | Evidence digest | Observed | Reason |
|---|---|---|---|---|---|
