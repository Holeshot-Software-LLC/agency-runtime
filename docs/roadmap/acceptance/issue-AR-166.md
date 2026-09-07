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
candidate_commit: pending
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
| 2 | test | Reconciliation failures retain visible failure notices and terminal state | 2026-09-07 | tests/dashboard_ui.test.mjs:5535-5557 |
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

All six current criteria await isolated candidate-bound verdicts. The builder
records evidence and observations only. Original criterion 1 is preserved;
criteria 2–6 are unchanged.

| Criterion | Verdict | Verifier run | Evidence digest | Observed | Reason |
|---|---|---|---|---|---|
