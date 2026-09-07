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
candidate_commit: 9419e68899194057f6ae8697d0ca17101ec16205
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
