---
title: "AR-151 acceptance verification record"
status: active
category: roadmap
created: 2026-09-07
updated: 2026-09-07
tags: [acceptance, verification, dashboard, hosts]
related:
  - docs/roadmap/issue-AR-151-align-route-lab-host-eligibility.md
  - docs/roadmap/acceptance/evidence/AR-151-host-eligibility-20260907.md
supersedes: []
superseded_by: null
type: acceptance-verification
issue_id: AR-151
candidate_commit: 99e05d1f46673068e65992fe6e60697c61b133d3
evidence_cutoff: 2026-09-07
tracker_url: null
---

# AR-151 acceptance verification record

## Builder evidence

| Criterion | Kind | Artifact | Observed | Source |
|---|---|---|---|---|
| 1 | file | Production renderer excludes duplicate identities and rejects an oversized inventory before enabling selection | 2026-09-07 | agency_runtime/dashboard/dashboard-render.js:1043-1122 |
| 1 | test | Duplicate-only and oversized inventories disable Route Lab without issuing a request | 2026-09-07 | tests/dashboard_ui.test.mjs:2307-2364 |
| 1 | test | Real GET projection and production UI exclude normalized/triple duplicates and eleven rows; ten rows and unrelated unique hosts follow server eligibility | 2026-09-07 | tests/test_dashboard.py:4704-4816 |
| 1 | command-output | Direct 13-case matrix and all 274 dashboard cases pass | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-151-host-eligibility-20260907.md#final-current-verification |
| 2 | file | Server derives eligibility from verified native evidence and independently rejects duplicate, unavailable and oversized records | 2026-09-07 | agency_runtime/server/dashboard.py:758-895 |
| 2 | file | POST checks host identity before catalog capture and passes only server-derived capabilities to inference | 2026-09-07 | agency_runtime/server/dashboard.py:2762-2821 |
| 2 | test | Production JavaScript constructs the exact outgoing request bodies from actual GET projection | 2026-09-07 | tests/dashboard_route_contract.mjs:1-55 |
| 2 | test | All five valid hosts reach actual POST; every excluded host is separately forged and rejected before inference | 2026-09-07 | tests/test_dashboard.py:4704-4816 |
| 2 | command-output | Direct UI-to-POST matrix scope and current passing results | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-151-host-eligibility-20260907.md#direct-ui-to-post-matrix |
| 3 | file | Static unavailable reasons explain ambiguous and oversized evidence without embedding host payloads | 2026-09-07 | agency_runtime/dashboard/dashboard-render.js:1093-1119 |
| 3 | test | UI renders the explicit ambiguity and size-bound reasons | 2026-09-07 | tests/dashboard_ui.test.mjs:2307-2364 |
| 3 | test | Actual GET projection rendered through production code has the expected reason and remains at most 160 characters | 2026-09-07 | tests/test_dashboard.py:4704-4816 |
| 4 | command-output | Final corrected six-module dashboard suite passes 274 with no skips; named spine passes 1085 with three existing skips | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-151-host-eligibility-20260907.md#final-current-verification |
| 4 | command-output | Complete UI suite passes 176 and exact current source-only coverage floors | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-151-host-eligibility-20260907.md#initial-dashboard-verification |
| 4 | command-output | Initial nine failures and intermediate denial-message failures are preserved and fixture repairs explained | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-151-host-eligibility-20260907.md#fixture-reconciliation |
| 4 | test | HTTP/production-renderer contract spans all supported hosts and rejection shapes | 2026-09-07 | tests/test_dashboard.py:4704-4816 |
| 4 | file | Current CI source-only UI denominator and 95/86/93 floors | 2026-09-07 | .github/workflows/ci.yml:279-285 |

## Verification

No verdicts supplied yet; the isolated runner owns this table.

| Criterion | Verdict | Verifier run | Evidence digest | Observed | Reason |
|---|---|---|---|---|---|
| 1 | contradicted | `AR-151.1-20260907-d1419f31` | `dea17c861100f61e4840805898470eb366e2b56686e828db5ad6986fdf37dde5` | 2026-09-07 | dashboard-render.js:1043-1122 permits unique hosts within duplicate inventories, and tests/test_dashboard.py:4704-4816 explicitly expects duplicate_with_valid to enable Route Lab for claude. |
| 2 | satisfied | `AR-151.2-20260907-7a2b350d` | `aed04dbff6d57852bf8b01ea7ab7ccaa1b546754d817d1c6db7250052cd02c01` | 2026-09-07 | The production-module driver in tests/dashboard_route_contract.mjs and the 13 passing UI-to-POST scenarios in tests/test_dashboard.py demonstrate that browser choices are accepted and excluded hosts are rejected by the authoritative POST handler. |
| 3 | satisfied | `AR-151.3-20260907-0e1e161e` | `b6a9a3e64a9a293f5597794b8942eb64832f4a2ea1616e69843143d64357e8b2` | 2026-09-07 | dashboard-render.js:1093-1119 renders a fixed ambiguity reason; dashboard_ui.test.mjs:2307-2364 checks its display, and test_dashboard.py:4704-4816 asserts duplicate scenarios show that reason within 160 characters. |
| 4 | satisfied | `AR-151.4-20260907-b9e33ce5` | `69ec484c78e3100fde5ff4f7305cb708e02c6fec6f5451a8351229d69a2b2b7b` | 2026-09-07 | The cited verification record reports 274 dashboard tests passing without skips, including 13 UI-to-POST scenarios, and 176 UI tests passing; tests/test_dashboard.py:4704-4816 demonstrates the HTTP contract assertions. |
