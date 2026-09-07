---
title: "AR-170 acceptance verification record"
status: active
category: roadmap
created: 2026-09-07
updated: 2026-09-07
tags: [acceptance, verification, dashboard, security]
related:
  - docs/roadmap/issue-AR-170-fail-dashboard-response-correlation-closed.md
  - docs/roadmap/acceptance/evidence/AR-170-response-correlation-20260907.md
  - docs/decisions/0230-reconcile-response-correlation-with-owner-controls.md
supersedes: []
superseded_by: null
type: acceptance-verification
issue_id: AR-170
candidate_commit: 91273e4128b2a8bc666edd8fcf6023c534a5d55e
evidence_cutoff: 2026-09-07
tracker_url: null
---

# AR-170 acceptance verification record

## Builder evidence

| Criterion | Kind | Artifact | Observed | Source |
|---|---|---|---|---|
| 1 | file | Response slug must exactly match normalized requested slug and have nonempty primitive worker identity | 2026-09-07 | agency_runtime/dashboard/dashboard-actions.js:38-65 |
| 1 | file | Worker selection validates inside its correlated request before current-generation state commit | 2026-09-07 | agency_runtime/dashboard/dashboard-actions.js:358-378 |
| 1 | test | Wrong slug, case, whitespace and nonstring response identities reject | 2026-09-07 | tests/dashboard_ui.test.mjs:5138-5176 |
| 1 | test | Invalid detail retains last-good worker and sent request ID | 2026-09-07 | tests/dashboard_ui.test.mjs:5200-5214 |
| 1 | command-output | Full current UI passes after reproduced repairs | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-170-response-correlation-20260907.md#fresh-verification |
| 2 | file | Safe nonnegative revision and each of four arrays are checked before returning detail | 2026-09-07 | agency_runtime/dashboard/dashboard-actions.js:38-65 |
| 2 | test | Unsafe revision and missing or nonarray evidence reject | 2026-09-07 | tests/dashboard_ui.test.mjs:5160-5198 |
| 2 | test | Negative revision and absent evidence never replace last-good detail | 2026-09-07 | tests/dashboard_ui.test.mjs:5200-5214 |
| 2 | command-output | Current UI and named spine results | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-170-response-correlation-20260907.md#fresh-verification |
| 3 | file | Exact primitive filter and each row slug match; multiple rows and fabricated pagination reject | 2026-09-07 | agency_runtime/dashboard/dashboard-live.js:1905-1921 |
| 3 | file | Control lookup captures request slug/path and validates before collection processing | 2026-09-07 | agency_runtime/dashboard/dashboard-live.js:1972-2010 |
| 3 | file | Current server exact lookup is zero/one-row with false truncation and null cursor | 2026-09-07 | agency_runtime/server/dashboard.py:2502-2536 |
| 3 | test | Exact lookup identity rejects wrong rows, case, whitespace and nonstrings | 2026-09-07 | tests/dashboard_ui.test.mjs:6138-6180 |
| 3 | test | Unexpected pagination rejects before wrong-worker second-page fetch, preserving prior roster | 2026-09-07 | tests/dashboard_ui.test.mjs:5216-5239 |
| 3 | command-output | UI and focused backend lookup tests pass | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-170-response-correlation-20260907.md#fresh-verification |
| 4 | file | Protected header normalization and exact sent UUID checks precede success or error return | 2026-09-07 | agency_runtime/dashboard/dashboard-core.js:339-403 |
| 4 | test | Object and browser Headers inputs cannot override protected fields; malformed IDs reject safely | 2026-09-07 | tests/dashboard_ui.test.mjs:909-989 |
| 4 | test | Twelve present-invalid body ID combinations reject even with matching response header | 2026-09-07 | tests/dashboard_ui.test.mjs:991-1013 |
| 4 | command-output | Real browser rejects null body ID while retaining exact safe ID | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-170-response-correlation-20260907.md#final-browser-sweep |
| 5 | file | Current worker validation failures retain request identity; stale generations cannot commit or overwrite notices | 2026-09-07 | agency_runtime/dashboard/dashboard-actions.js:358-378 |
| 5 | file | Request helper wraps pure structural validation errors with generated identity | 2026-09-07 | agency_runtime/dashboard/dashboard-core.js:339-403 |
| 5 | file | Current control failure preserves last-good revision and exposes its safe request ID | 2026-09-07 | agency_runtime/dashboard/dashboard-live.js:2028-2042 |
| 5 | test | Wrong worker and fabricated exact pagination leave prior state untouched with correlated errors | 2026-09-07 | tests/dashboard_ui.test.mjs:5200-5239 |
| 5 | test | Stale exact lookup cannot roll back a newer successful filter and roster | 2026-09-07 | tests/dashboard_ui.test.mjs:6691-6752 |
| 5 | command-output | Current browser retained-state notice and exact request identity | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-170-response-correlation-20260907.md#final-browser-sweep |
| 6 | file | Explicit reconciliation applies current owner authority, preserving original criterion | 2026-09-07 | docs/decisions/0230-reconcile-response-correlation-with-owner-controls.md#decision |
| 6 | file | Configuration refresh preserves dirty revision baseline and pending snapshot | 2026-09-07 | agency_runtime/dashboard/dashboard-config.js:502-549 |
| 6 | test | Semantic hidden/inactive views remain excluded from rendering | 2026-09-07 | tests/dashboard_ui.test.mjs:5241-5280 |
| 6 | test | Owner controls and clean draft state survive config render with no draft save | 2026-09-07 | tests/dashboard_ui.test.mjs:8157-8231 |
| 6 | test | Every broker mutation denies and leaves state unchanged | 2026-09-07 | tests/test_dashboard.py:392-413 |
| 6 | command-output | Fresh backend and full UI pass | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-170-response-correlation-20260907.md#fresh-verification |
| 6 | command-output | Real browser hidden/layout invariants and owner controls after asynchronous refresh | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-170-response-correlation-20260907.md#final-browser-sweep |
| 7 | file | Explicit owner-maintenance reconciliation preserves original wording | 2026-09-07 | docs/decisions/0230-reconcile-response-correlation-with-owner-controls.md#decision |
| 7 | file | Token scrubbing preserves ordinary in-page fragments | 2026-09-07 | agency_runtime/dashboard/dashboard-core.js:405-420 |
| 7 | test | Maintenance markup and real owner controls match actual authority | 2026-09-07 | tests/dashboard_ui.test.mjs:8157-8213 |
| 7 | command-output | Primary desktop overview/routing/evidence heading dimensions and hidden invariants | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-170-browser-20260907/final/report.json:1-63 |
| 7 | command-output | Primary desktop remaining views and actual keyboard skip-link pass | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-170-browser-20260907/final/report.json:121-182 |
| 7 | command-output | Primary mobile settings layout, keyboard focus, exact source hashes and final pass | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-170-browser-20260907/final/report.json:309-382 |
| 7 | command-output | Git proves browser and candidate dashboard/test tree identity, with no source diff | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-170-response-correlation-20260907.md#source-identity |
| 7 | command-output | Exact scope and method of the source-served keyboard/layout sweep | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-170-response-correlation-20260907.md#final-browser-sweep |
| 8 | command-output | Fresh actual UI stdout, production coverage and focused verification | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-170-response-correlation-20260907.md#fresh-verification |
| 8 | command-output | Actual Git object equality binds the browser run to unchanged candidate source/tests | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-170-response-correlation-20260907.md#source-identity |
| 8 | command-output | Primary seven-view/six-tab sweep part one | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-170-browser-20260907/final/report.json:1-100 |
| 8 | command-output | Primary seven-view/six-tab sweep part two | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-170-browser-20260907/final/report.json:101-200 |
| 8 | command-output | Primary seven-view/six-tab sweep part three | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-170-browser-20260907/final/report.json:201-300 |
| 8 | command-output | Primary sweep completion, no ordinary application errors, asset hashes and final pass | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-170-browser-20260907/final/report.json:301-382 |
| 8 | command-output | Browser fixture scope and deliberately injected diagnostic separated from ordinary sweeps | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-170-response-correlation-20260907.md#final-browser-sweep |
| 9 | file | Explicit bounded verification reconciliation under existing ADR-0105 | 2026-09-07 | docs/decisions/0230-reconcile-response-correlation-with-owner-controls.md#decision |
| 9 | command-output | UI/current floors, fresh named spine, focused backend, actual asset check and Ruff pass | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-170-response-correlation-20260907.md#fresh-verification |
| 9 | command-output | Current exact-source browser proof and stated limits | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-170-response-correlation-20260907.md#final-browser-sweep |
| 9 | command-output | Metadata/policy/worklog, strict docs/tracker and diff pass | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-170-response-correlation-20260907.md#publication-validation |

## Verification

Second and final pass at 91273e4128b2a8bc666edd8fcf6023c534a5d55e: 1/2/4/5/6/7/8 satisfy;
3/9 remain absent for complete call-site and raw gate-receipt evidence.
All first verdicts remain at 662eb947. Keep AR-170 in_progress; do not copy
earlier verdicts across candidates or run an unapproved third review.

| Criterion | Verdict | Verifier run | Evidence digest | Observed | Reason |
|---|---|---|---|---|---|
| 1 | satisfied | `AR-170.1-20260907-d36b59d7` | `0b92d681224f48259e79435f66c4d27d1818c87798d3e7ca6f7ebc50022f37be` | 2026-09-07 | dashboard-actions.js:38-65 and 358-378 enforce exact requested slug matching before committing worker detail; dashboard_ui.test.mjs:5138-5176 verifies rejection of wrong, case-altered, whitespace-padded, and nonstring response slugs. |
| 2 | satisfied | `AR-170.2-20260907-0fc4cadc` | `f07060e0f0662f2f6a0fe51ba44d17af2ffbdae8612766c33862666d49e064e5` | 2026-09-07 | dashboard-actions.js:38-65 requires a safe nonnegative revision and all four evidence arrays; dashboard_ui.test.mjs:5160-5214 verifies rejection of invalid evidence and retention of last-good detail. |
| 3 | absent | `AR-170.3-20260907-d1600fe7` | `03fb4e0de31494aa37dfffe4be46ce46a8e4a17a619ee4fc6fe7fbe501476ea2` | 2026-09-07 | dashboard-live.js:1905-1921 and 1972-2010 demonstrate control lookup validation, but completeRosterPage and other collection call sites are not shown, so coverage of every current paginated path cannot be established. |
| 4 | satisfied | `AR-170.4-20260907-ee544f27` | `3a47d929e03ebb12f62cca14f4a927777465121c3ccc3c88ec9028e2acd4cc1a` | 2026-09-07 | dashboard-core.js:339-403 overwrites protected caller headers, validates the sent UUID, and rejects every present response ID unequal to it; dashboard_ui.test.mjs:909-1013 covers overrides, mismatches, malformed IDs, and invalid body values. |
| 5 | satisfied | `AR-170.5-20260907-f1f31a10` | `9df406dae47cb9c94f64f078027a53a74ffcf5d847aecb60c9262e6a879c5158` | 2026-09-07 | dashboard-core.js wraps invalid responses with request IDs, dashboard-live.js exposes retained-state failures, and dashboard-actions.js plus the cited UI tests demonstrate preservation of last-good state and rejection of stale updates. |
| 6 | satisfied | `AR-170.6-20260907-27794010` | `22bbe65915d554259f251b4736df821af47fec1ea3b38ec474881be54d2e5ed4` | 2026-09-07 | dashboard-config.js preserves dirty drafts and pending revisions; dashboard_ui.test.mjs verifies semantic hiding and owner controls after rendering; test_dashboard.py verifies broker mutations return 403 without state changes. |
| 7 | satisfied | `AR-170.7-20260907-aa302d86` | `23ed41276bf4a0671d878eb69eebce29ea9cd56d7aa4520c56b23a8fab717e1d` | 2026-09-07 | The final browser report records passing desktop heading and keyboard skip-link checks; dashboard-core.js preserves ordinary fragments, and dashboard_ui.test.mjs shows maintenance copy consistent with enabled owner controls under ADR-0230. |
| 8 | satisfied | `AR-170.8-20260907-b7ac3472` | `8fc7547c8f361cda49025741d56531783e846a8554c07928f95e890c5e22454e` | 2026-09-07 | Fresh-verification records 193 UI tests passing; final/report.json records passing seven-view/six-tab sweeps at both widths without application errors, with injected diagnostics separated; source-identity records unchanged source/test trees. |
| 9 | absent | `AR-170.9-20260907-5ede9bf1` | `e39dbcd8aa56410668fcbe049a76d8bc92ab8e387f9931819141ae32b807e735` | 2026-09-07 | The evidence document includes UI test output, but coverage, production spine, browser, metadata, policy, worklog, docs/tracker, Ruff and diff passes are summaries without supporting receipts bound to the candidate commit. |
