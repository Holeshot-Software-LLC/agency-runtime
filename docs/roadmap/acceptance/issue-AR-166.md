---
title: "AR-166 acceptance verification record"
status: active
category: roadmap
created: 2026-09-07
updated: 2026-09-07
tags: [acceptance, verification, dashboard, security]
related:
  - docs/roadmap/issue-AR-166-truthful-dashboard-disclosure-and-correlation.md
  - docs/roadmap/acceptance/evidence/AR-166-dashboard-authority-20260907.md
  - docs/decisions/0229-reconcile-dashboard-disclosure-with-owner-authority.md
supersedes: []
superseded_by: null
type: acceptance-verification
issue_id: AR-166
candidate_commit: 4a24477669e1b773b27626f2cd67631fbe78f875
evidence_cutoff: 2026-09-07
tracker_url: null
---

# AR-166 acceptance verification record

## Builder evidence

| Criterion | Kind | Artifact | Observed | Source |
|---|---|---|---|---|
| 1 | file | Explicit reconciliation applies current owner authority and preserves the original first criterion | 2026-09-07 | docs/decisions/0229-reconcile-dashboard-disclosure-with-owner-authority.md#decision |
| 1 | file | Only valid nonempty provider lists enable the selector, with selection preservation | 2026-09-07 | agency_runtime/dashboard/dashboard-config.js:198-224 |
| 1 | test | Stored-key redaction, second-provider choice, exact staged secret target, disabled lists and recovery | 2026-09-07 | tests/dashboard_ui.test.mjs:1053-1143 |
| 1 | test | Every broker mutation is rejected without state changes | 2026-09-07 | tests/test_dashboard.py:392-413 |
| 1 | command-output | Current UI and owner/backend suites pass | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-166-dashboard-authority-20260907.md#fresh-verification |
| 1 | command-output | Real source-served desktop/mobile owner interaction and no-write check | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-166-dashboard-authority-20260907.md#browser-checkpoint |
| 2 | file | UUIDv4 validation and APIError retain only safe identifiers in messages | 2026-09-07 | agency_runtime/dashboard/dashboard-core.js:15-38 |
| 2 | file | Transport and HTTP errors retain generated IDs; mismatched correlation is rejected and null errors are safe | 2026-09-07 | agency_runtime/dashboard/dashboard-core.js:339-411 |
| 2 | file | Terminal authentication notices and reconnection failures validate forwarded request IDs | 2026-09-07 | agency_runtime/dashboard/dashboard-live.js:1268-1306 |
| 2 | test | HTTP/mismatched identity rejection and null-body 401/403/503 retain status and safe IDs | 2026-09-07 | tests/dashboard_ui.test.mjs:943-1007 |
| 2 | test | Network failures retain the safe browser request identity | 2026-09-07 | tests/dashboard_ui.test.mjs:1975-1998 |
| 2 | test | Terminal 401/403 notices include the safe request ID | 2026-09-07 | tests/dashboard_ui.test.mjs:5322-5360 |
| 2 | file | Both reconciliation paths forward the existing APIError message; runtime reconciliation delegates terminal failures to the safe ID handler | 2026-09-07 | agency_runtime/dashboard/dashboard-live.js:2451-2477 |
| 2 | command-output | Fresh complete UI cases exercise all listed paths | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-166-dashboard-authority-20260907.md#fresh-verification |
| 3 | file | Only canonical UUIDv4 values survive display validation | 2026-09-07 | agency_runtime/dashboard/dashboard-core.js:15-25 |
| 3 | file | Receipt rendering adds request identity only after validation | 2026-09-07 | agency_runtime/dashboard/dashboard-render.js:1810-1850 |
| 3 | test | A successful real UI route flow renders the exact generated request ID | 2026-09-07 | tests/dashboard_ui.test.mjs:4935-4997 |
| 3 | test | Hostile receipt identity remains absent from rendered text | 2026-09-07 | tests/dashboard_ui.test.mjs:2719-2740 |
| 3 | command-output | Complete current UI suite passes | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-166-dashboard-authority-20260907.md#fresh-verification |
| 4 | file | Bootstrap replaces the ambiguous initial privacy chip | 2026-09-07 | agency_runtime/dashboard/app.js:158-166 |
| 4 | file | Config capture setting explicitly names redacted runtime content or runtime metadata | 2026-09-07 | agency_runtime/dashboard/dashboard-config.js:122-144 |
| 4 | file | Overview refresh retains the explicit runtime-capture distinction | 2026-09-07 | agency_runtime/dashboard/dashboard-render.js:515-529 |
| 4 | test | Config snapshots assert both capture states and labels | 2026-09-07 | tests/dashboard_ui.test.mjs:2106-2138 |
| 4 | command-output | Real browser interaction retains Runtime metadata only at both viewport widths | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-166-dashboard-authority-20260907.md#browser-checkpoint |
| 5 | file | Worker detail labels governed stored definition and explicitly disclaims runtime delivery | 2026-09-07 | agency_runtime/dashboard/dashboard-render.js:2120-2137 |
| 5 | file | Store validates prompt identity and bounds complete content with truncation provenance | 2026-09-07 | agency_runtime/core/store/workforce.py:2085-2175 |
| 5 | file | Dashboard owner detail requests at most 262144 characters | 2026-09-07 | agency_runtime/server/dashboard.py:2232-2236 |
| 5 | file | Model-facing broker allow-list excludes workforce detail | 2026-09-07 | agency_runtime/core/dashboard_runtime.py:44-76 |
| 5 | file | Owner/broker credentials, origin and endpoint scope are enforced before reads | 2026-09-07 | agency_runtime/server/dashboard.py:1542-1591 |
| 5 | test | Owner detail returns governed content/provenance through the real server | 2026-09-07 | tests/test_dashboard.py:889-943 |
| 5 | test | Owner detail labels full prompt, Store authority and no runtime-delivery assertion | 2026-09-07 | tests/dashboard_ui.test.mjs:1355-1379 |
| 5 | command-output | Current owner/backend tests pass; no backend or broker-policy change | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-166-dashboard-authority-20260907.md#fresh-verification |
| 6 | command-output | Full UI with current coverage floors, focused backend, named spine and Ruff pass | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-166-dashboard-authority-20260907.md#fresh-verification |
| 6 | command-output | Metadata, strict docs/tracker, policy, exact worklog and diff checks pass | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-166-dashboard-authority-20260907.md#publication-validation |

## Verification

All six current criteria satisfy at 4a24477669e1b773b27626f2cd67631fbe78f875.
Criteria 1 and 3–6 retain their first verdicts. Criterion 2 satisfies after one
citation-only recheck of existing reconciliation forwarding. All first verdicts,
including the absent result, remain at bc28bf66. No source, test, candidate or
criterion changed for that recheck.

| Criterion | Verdict | Verifier run | Evidence digest | Observed | Reason |
|---|---|---|---|---|---|
| 1 | satisfied | `AR-166.1-20260907-cbb8615e` | `d4b0ca70289e27b2567a03ecf10802ba772bbfdf76e5f3e2b8653cfcfc460d88` | 2026-09-07 | dashboard-config.js:198-224 preserves valid selections and disables invalid lists; dashboard_ui.test.mjs:1053-1143 covers key redaction and recovery; test_dashboard.py:392-413 verifies broker denial without mutations, with passing suites recorded in the cited verification artifact. |
| 3 | satisfied | `AR-166.3-20260907-5a2b58a2` | `18bfe1e9b6e58ebd79c8d98debcf3f9aeec8723ad42174f2d58c8c3c9dca66d1` | 2026-09-07 | dashboard-core.js validates UUIDv4 IDs, dashboard-render.js conditionally renders validated IDs, and dashboard_ui.test.mjs asserts exact successful-route ID display and omission of a hostile malformed ID. |
| 4 | satisfied | `AR-166.4-20260907-df7e4d7b` | `809ad9c1ddc6f8492defcc20a09da46412f82811e619068bfb5cc337c87dc2cd` | 2026-09-07 | dashboard-config.js:122-144 and dashboard-render.js:515-529 set the privacy chip to “Redacted runtime content” or “Runtime metadata only” based on observability capture state; tests/dashboard_ui.test.mjs:2106-2138 asserts both labels. |
| 5 | satisfied | `AR-166.5-20260907-4288fb08` | `366523e150dc9e9dfeb8ac4b91e0dc7fe952a689d3f04f1cd639f6caae60756b` | 2026-09-07 | dashboard-render.js distinguishes stored definitions from runtime delivery, workforce.py and dashboard.py bound content to 262144 characters, broker allow-lists exclude workforce detail, and the verification report records unchanged authentication and broker policy. |
| 6 | satisfied | `AR-166.6-20260907-808b5876` | `d1a7713ce4c535d48ba2d188743886373d01ea2d58d11f3a149e2739c90c3d1e` | 2026-09-07 | The cited evidence document’s Fresh verification and Publication validation sections record 190 passing UI tests, strict documentation checks, Ruff check/format passing for 766 files, and zero diff-check errors. |
| 2 | satisfied | `AR-166.2-20260907-adabbd41` | `a995a17850183137b7dd48f82197d511fb6a95170872b0540ea686b297189fea` | 2026-09-07 | dashboard-core.js validates request IDs and preserves the generated ID for HTTP and transport errors; dashboard-live.js forwards safe IDs through authentication and reconciliation notices, supported by the cited UI tests. |
