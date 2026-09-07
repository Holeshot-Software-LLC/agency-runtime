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
candidate_commit: 06aee2ede122ce48362d532886e537bf5fd1d80a
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
| 7 | file | Only owner-maintenance wording replaces the retired attended-only policy | 2026-09-07 | docs/decisions/0230-reconcile-response-correlation-with-owner-controls.md#decision |
| 7 | file | Ordinary in-page fragments remain intact while token fragments are scrubbed | 2026-09-07 | agency_runtime/dashboard/dashboard-core.js:405-420 |
| 7 | test | Non-token navigation retains its native fragment | 2026-09-07 | tests/dashboard_ui.test.mjs:827-840 |
| 7 | test | Current maintenance markup and owner action wiring agree | 2026-09-07 | tests/dashboard_ui.test.mjs:8157-8213 |
| 7 | command-output | All views fit both widths; actual keyboard Enter focuses main content | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-170-response-correlation-20260907.md#final-browser-sweep |
| 8 | command-output | Full focused UI and current production-only floors pass | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-170-response-correlation-20260907.md#fresh-verification |
| 8 | command-output | Thirty-four source-served checks across all seven views/six tabs, zero ordinary sweep application errors | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-170-response-correlation-20260907.md#final-browser-sweep |
| 9 | file | Explicit bounded verification reconciliation under existing ADR-0105 | 2026-09-07 | docs/decisions/0230-reconcile-response-correlation-with-owner-controls.md#decision |
| 9 | command-output | UI/current floors, fresh named spine, focused backend, actual asset check and Ruff pass | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-170-response-correlation-20260907.md#fresh-verification |
| 9 | command-output | Current exact-source browser proof and stated limits | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-170-response-correlation-20260907.md#final-browser-sweep |
| 9 | command-output | Metadata/policy/worklog, strict docs/tracker and diff pass | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-170-response-correlation-20260907.md#publication-validation |

## Verification

Pending isolated checks at the frozen candidate.

| Criterion | Verdict | Verifier run | Evidence digest | Observed | Reason |
|---|---|---|---|---|---|
| 1 | satisfied | `AR-170.1-20260907-86c822a9` | `8fa611434309e24c38257d5248cdfc3760300233388e4df85eff422a62e19bc3` | 2026-09-07 | dashboard-actions.js:38-65 enforces exact normalized requested-slug equality and valid worker identity; lines 358-378 validate before committing current-request detail, supported by rejection and retained-state tests in dashboard_ui.test.mjs. |
| 2 | satisfied | `AR-170.2-20260907-b45447d7` | `2715a1366d5ce3a575e1e2f4059c1d7e4ced51c1749c949bb5001b5c8ea2fe9e` | 2026-09-07 | dashboard-actions.js:38-65 rejects unsafe or negative revisions and requires all four evidence arrays; dashboard_ui.test.mjs:5160-5214 verifies invalid evidence rejection and retention of last-good detail. |
| 3 | satisfied | `AR-170.3-20260907-dcf8fdeb` | `2d9fdf818d54d06726936e3124cfcc78eef023526f21f50f2a7dc3f2eee5b336` | 2026-09-07 | dashboard-live.js validates the requested slug and every returned row before collection processing and rejects pagination; dashboard_ui.test.mjs verifies mismatches and blocks a wrong-worker second-page fetch. |
| 4 | satisfied | `AR-170.4-20260907-857d635f` | `e79e5e0d0189ec1b865760ac255981b5c776d7fb55ab1593670fb5e4766da21d` | 2026-09-07 | dashboard-core.js:339-403 overwrites protected caller headers, validates the sent UUID, and rejects every present response ID unequal to it; dashboard_ui.test.mjs:909-1013 covers overrides and invalid response IDs. |
| 5 | satisfied | `AR-170.5-20260907-de7960d8` | `47c7e33c4e3377dafcbac07424ec5772cff95b079113dcc64bf433289006cb3b` | 2026-09-07 | dashboard-actions.js guards stale commits, dashboard-core.js correlates validation errors, and dashboard-live.js reports retained state; the cited worker and roster tests assert preservation of last-good state. |
| 6 | satisfied | `AR-170.6-20260907-8f352624` | `5d75268cecb8872c3ba75072d14b6494da9dc2aac7b3bf2e91840c3803134db2` | 2026-09-07 | dashboard-config.js preserves dirty drafts during refresh; dashboard_ui.test.mjs verifies hidden panels and truthful owner controls; test_dashboard.py verifies broker mutations are denied without state changes, corroborated by the browser sweep receipt. |
| 7 | absent | `AR-170.7-20260907-0f20071a` | `11cb7c76a99d6dd1bd43c0748d2cd044d72b35dfc7ca58a8b597b413a060d8c5` | 2026-09-07 | The code and test excerpts support fragment preservation and owner controls, but the browser-sweep excerpt cites a different commit and an unavailable report; heading layout and actual keyboard focus at the candidate commit remain unverified. |
| 8 | absent | `AR-170.8-20260907-04faa1a1` | `fc3213f8208d185d94d96af825eeacf693ea28b82d7e7e65328527b2fbfc918a` | 2026-09-07 | The cited Markdown summarizes passing runs at f1ff818, but final/report.json and focused-suite output are unavailable, and the excerpts do not establish those results at candidate 06aee2e. |
| 9 | satisfied | `AR-170.9-20260907-a04c2de1` | `74da303532f7ad754f9d19772a6b80b6e9fcccb18f27518606db461b93e1d65e` | 2026-09-07 | AR-170 evidence sections Fresh verification, Final browser sweep and Publication validation record passing UI coverage floors, production spine, scoped browser and required checks; ADR-0230 keeps exhaustive gates optional. |
