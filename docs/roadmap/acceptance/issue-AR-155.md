---
title: "AR-155 acceptance verification record"
status: active
category: roadmap
created: 2026-09-07
updated: 2026-09-07
tags: [acceptance, verification, dashboard, hiring]
related:
  - docs/roadmap/issue-AR-155-bound-dashboard-hiring-evidence.md
  - docs/roadmap/acceptance/evidence/AR-155-hiring-evidence-20260907.md
  - docs/decisions/0105-bound-delivery-to-live-demo-checkpoints.md
supersedes: []
superseded_by: null
type: acceptance-verification
issue_id: AR-155
candidate_commit: 6ed2494345e2810741eec430700ebce540e9b4b4
evidence_cutoff: 2026-09-07
tracker_url: null
---

# AR-155 acceptance verification record

## Builder evidence

| Criterion | Kind | Artifact | Observed | Source |
|---|---|---|---|---|
| 1 | file | Collection SQL selects only summary metadata and projects evidence_included false | 2026-09-07 | agency_runtime/core/store/workforce.py:1574-1607 |
| 1 | test | Every row in a 200-row Store collection omits all five evidence fields | 2026-09-07 | tests/test_workforce_lifecycle.py:728-780 |
| 1 | test | HTTP collection omits fields and the large private document marker | 2026-09-07 | tests/test_dashboard.py:1030-1090 |
| 1 | command-output | Fresh Store/HTTP collection cases pass | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-155-hiring-evidence-20260907.md#fresh-focused-checks |
| 2 | file | Explicit 200-row limit, 1 MiB budget and metadata reserve | 2026-09-07 | agency_runtime/core/store/workforce.py:35-38 |
| 2 | file | Store byte budget and fail-closed exception | 2026-09-07 | agency_runtime/core/store/workforce.py:1595-1607 |
| 2 | file | HTTP response enforces the collection budget including response metadata | 2026-09-07 | agency_runtime/server/dashboard.py:2297-2363 |
| 2 | test | Complete 200-row HTTP response is within budget with truthful Content-Length | 2026-09-07 | tests/test_dashboard.py:1030-1090 |
| 2 | test | Deliberately oversized HTTP/Store projections fail generically | 2026-09-07 | tests/test_dashboard.py:1093-1141 |
| 2 | command-output | Fresh bounded-list and budget-failure regressions pass | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-155-hiring-evidence-20260907.md#fresh-focused-checks |
| 3 | file | Exact lookup decodes and returns all five governed evidence documents | 2026-09-07 | agency_runtime/core/store/workforce.py:1420-1439 |
| 3 | file | Exact HTTP case lookup is separate from the collection byte cap | 2026-09-07 | agency_runtime/server/dashboard.py:2297-2363 |
| 3 | test | Exact HTTP response exceeds 1 MiB and preserves equality for every document | 2026-09-07 | tests/test_dashboard.py:1030-1090 |
| 3 | test | Exact Store documents equal the complete large inputs | 2026-09-07 | tests/test_workforce_lifecycle.py:728-780 |
| 3 | command-output | Exact-evidence equality checks pass with bounded-list regressions | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-155-hiring-evidence-20260907.md#fresh-focused-checks |
| 4 | file | One explicit delegated click calls exact evidence loading | 2026-09-07 | agency_runtime/dashboard/app.js:460-476 |
| 4 | file | Exact evidence validates identity/documents and commits only for the current request | 2026-09-07 | agency_runtime/dashboard/dashboard-live.js:2274-2351 |
| 4 | test | Rendering summaries does not fetch; explicit inspection loads all five documents | 2026-09-07 | tests/dashboard_ui.test.mjs:1399-1455 |
| 4 | test | An aborted old response delivered after a newer case cannot replace it | 2026-09-07 | tests/dashboard_ui.test.mjs:1525-1554 |
| 4 | test | Teardown aborts the request and rejects its late response | 2026-09-07 | tests/dashboard_ui.test.mjs:1711-1761 |
| 4 | command-output | Complete 188-test UI suite passes including explicit inspection and stale rejection | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-155-hiring-evidence-20260907.md#fresh-focused-checks |
| 5 | command-output | Fresh four focused Store/HTTP cases, 25 lifecycle cases and 188 UI cases pass current coverage floors | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-155-hiring-evidence-20260907.md#fresh-focused-checks |
| 5 | command-output | Exact-byte binding for broader dashboard and warning-strict named spine reuse | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-155-hiring-evidence-20260907.md#exact-byte-broader-evidence |
| 5 | command-output | Exact six-module dashboard and named-spine commands/results for unchanged Python source/tests | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-151-host-eligibility-20260907.md#final-current-verification |
| 5 | file | Existing bounded-delivery policy makes exhaustive diagnostics optional | 2026-09-07 | docs/decisions/0105-bound-delivery-to-live-demo-checkpoints.md#decision |

## Verification

No verdicts supplied yet; the isolated runner owns this table. Criterion 5 is
explicitly reconciled under ADR-0105; the issue retains the original wording.

| Criterion | Verdict | Verifier run | Evidence digest | Observed | Reason |
|---|---|---|---|---|---|
