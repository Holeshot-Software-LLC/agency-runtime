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

Initial runner execution supplied satisfied verdicts for criteria 1, 2, 4 and 5.
Criterion 3 returned "verifier unavailable or outside the vocabulary" and no
verdict was recorded; a3e00bd5 preserves that partial result. One isolated retry
of criterion 3 against the unchanged candidate supplied its satisfied verdict.
All five now satisfy. Criterion 5 is explicitly reconciled under ADR-0105;
the issue retains the original wording.

| Criterion | Verdict | Verifier run | Evidence digest | Observed | Reason |
|---|---|---|---|---|---|
| 1 | satisfied | `AR-155.1-20260907-b0ed192c` | `f88bafdd269479f5647ab3641127e54078dc2692f42749d54605cc3a83d04f8c` | 2026-09-07 | workforce.py selects only summary metadata; Store and HTTP tests assert all five evidence fields are absent from every collection row, and the cited focused-check receipt reports four passing tests. |
| 2 | satisfied | `AR-155.2-20260907-d95c1164` | `9ef8549fa9915aff3c2dbd2af4085508e45e490a46a30bc73d22cc3db1e30807` | 2026-09-07 | workforce.py sets a 200-row cap and 1 MiB budget; dashboard.py applies the budget to the complete response, and test_dashboard.py verifies 200 rows fit with accurate Content-Length and oversized responses fail closed. |
| 4 | satisfied | `AR-155.4-20260907-71a8a7bc` | `764fbf6a5eaa545906e417c04d6d2dfff01f9c67736d606b3d2f706c71790a4f` | 2026-09-07 | app.js:460-476 ties evidence loading to an explicit click; dashboard-live.js:2274-2351 guards response commits, and dashboard_ui.test.mjs verifies a single inspection fetch and rejection of stale and post-teardown responses. |
| 5 | satisfied | `AR-155.5-20260907-d18eb504` | `cd3ffb59e49077b644c65b7a0859f3cb0cab73c028519cf36b20f1dc4729c828` | 2026-09-07 | AR-155's evidence records 25 Store passes and 188 UI passes above production coverage floors, and binds unchanged sources to AR-151's 274 dashboard passes and 1,085 named warning-strict spine passes with three existing skips. |
| 3 | satisfied | `AR-155.3-20260907-10b5541d` | `07a13d2166892f8aec080587f7952ce79a905fbd33eddafd85573e732bbc1092` | 2026-09-07 | workforce.py returns all five decoded evidence documents, dashboard.py sends exact cases without the collection byte cap, and Store and HTTP tests assert full equality with large inputs. |
