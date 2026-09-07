---
title: "AR-175 acceptance verification record"
status: active
category: roadmap
created: 2026-09-07
updated: 2026-09-07
tags: [acceptance, verification, dashboard, correlation]
related:
  - docs/roadmap/issue-AR-175-retire-dashboard-control-fallback.md
  - docs/roadmap/acceptance/evidence/AR-175-control-boundary-20260907.md
  - docs/decisions/0105-bound-delivery-to-live-demo-checkpoints.md
supersedes: []
superseded_by: null
type: acceptance-verification
issue_id: AR-175
candidate_commit: 328c5634567e6b12a295bb5f8957c5541cc35dba
evidence_cutoff: 2026-09-07
tracker_url: null
---

# AR-175 acceptance verification record

## Builder evidence

| Criterion | Kind | Artifact | Observed | Source |
|---|---|---|---|---|
| 1 | file | Real server emits v1 for both normal and restart-required control envelopes | 2026-09-07 | agency_runtime/server/dashboard.py:1999-2080 |
| 1 | file | Client requires v1 through the authenticated API validator before applying control | 2026-09-07 | agency_runtime/dashboard/dashboard-live.js:1972-2016 |
| 1 | file | Authenticated API preserves sent IDs and rejects mismatched response IDs | 2026-09-07 | agency_runtime/dashboard/dashboard-core.js:339-409 |
| 1 | file | Real browser reads server schema and echoed headers before injecting faults | 2026-09-07 | scripts/verify_dashboard_browser.mjs:127-190 |
| 1 | command-output | Actual installed-wheel run and exact served source bytes | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-175-control-boundary-20260907.md#served-bytes-and-headers |
| 1 | command-output | All real-browser faults and views pass | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-175-control-boundary-20260907.md#browser-result-projection |
| 2 | file | Schema boundary and last-good application sequence | 2026-09-07 | agency_runtime/dashboard/dashboard-live.js:1972-2075 |
| 2 | file | API failure and correlation behavior | 2026-09-07 | agency_runtime/dashboard/dashboard-core.js:339-409 |
| 2 | file | Control refresh rejects obsolete work before applying its snapshot | 2026-09-07 | agency_runtime/dashboard/dashboard-live.js:2076-2126 |
| 2 | file | Full refresh applies no partial live or control snapshot on failure | 2026-09-07 | agency_runtime/dashboard/dashboard-live.js:2128-2201 |
| 2 | test | Twenty cases compare full baseline state and exact requests for both paths | 2026-09-07 | tests/dashboard_ui.test.mjs:4677-4754 |
| 2 | test | Late successful responses cannot cross lifecycle or full generations | 2026-09-07 | tests/dashboard_ui.test.mjs:4888-4921 |
| 2 | command-output | All twenty direct cases pass | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-175-control-boundary-20260907.md#focused-green-transcript |
| 2 | command-output | Thirty-six live faults retain state with zero legacy calls | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-175-control-boundary-20260907.md#browser-result-projection |
| 3 | file | Control owner quietly ignores abort, lifecycle and generation races | 2026-09-07 | agency_runtime/dashboard/dashboard-live.js:2076-2126 |
| 3 | file | Full owner quietly ignores abort, lifecycle and generation races | 2026-09-07 | agency_runtime/dashboard/dashboard-live.js:2128-2201 |
| 3 | test | Aborted valid or invalid, suspended and obsolete control responses remain quiet | 2026-09-07 | tests/dashboard_ui.test.mjs:4677-4754 |
| 3 | test | Late control and full successful responses remain uncommitted | 2026-09-07 | tests/dashboard_ui.test.mjs:4888-4921 |
| 3 | command-output | All twenty focused cases pass, including all eight cancellation cases | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-175-control-boundary-20260907.md#focused-green-transcript |
| 3 | command-output | Complete UI suite with stale success and failure races passes | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-175-control-boundary-20260907.md#full-ui-and-current-coverage-transcript |
| 4 | test | Missing endpoint and wrong-version contract retain state with only one request | 2026-09-07 | tests/dashboard_ui.test.mjs:4653-4674 |
| 4 | test | Both full and control paths assert exact request lists and retention | 2026-09-07 | tests/dashboard_ui.test.mjs:4677-4754 |
| 4 | file | Real-browser fault loop asserts actual headers, retention, no legacy calls and recovery | 2026-09-07 | scripts/verify_dashboard_browser.mjs:127-190 |
| 4 | command-output | Actual installed-wheel fault run with 404 and wrong-schema cases | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-175-control-boundary-20260907.md#loaded-browser-verification |
| 4 | command-output | Stored real-browser per-case result projection | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-175-control-boundary-20260907.md#browser-result-projection |
| 4 | command-output | All direct boundary cases pass | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-175-control-boundary-20260907.md#focused-green-transcript |
| 5 | test | Unchanged exact strict 378-KiB resource ceiling | 2026-09-07 | tests/test_release_packaging.py:273-323 |
| 5 | command-output | Resource and coverage-floor selectors pass with actual byte count | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-175-control-boundary-20260907.md#asset-gate |
| 5 | command-output | All ten served-resource hashes equal checked source | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-175-control-boundary-20260907.md#served-bytes-and-headers |
| 5 | command-output | Wheel and sdist identity, canonical verification and strict Twine | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-175-control-boundary-20260907.md#installed-artifact-identity |
| 6 | file | Existing bounded delivery authority and exhaustive integration scope | 2026-09-07 | docs/decisions/0105-bound-delivery-to-live-demo-checkpoints.md:62-84 |
| 6 | command-output | Current focused regressions | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-175-control-boundary-20260907.md:243-292 |
| 6 | command-output | Complete current UI and unchanged coverage floors | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-175-control-boundary-20260907.md:313-352 |
| 6 | command-output | Actual strict current asset gate | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-175-control-boundary-20260907.md:293-312 |
| 6 | command-output | Fresh named production spine command and complete stdout | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-175-control-boundary-20260907.md:367-393 |
| 6 | command-output | Fresh installed-wheel loaded browser execution | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-175-control-boundary-20260907.md:428-474 |
| 6 | command-output | Strict metadata policy worklog docs tracker Ruff and diff | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-175-control-boundary-20260907.md:519-564 |

## Verification

First verdicts are preserved in 8ed3c516. Criteria 1–5 are satisfied at the
unchanged candidate. Only criterion 6 is rechecked after limiting overlapping
heading excerpts to exact lines; no source, criterion or prior verdict is changed.

| Criterion | Verdict | Verifier run | Evidence digest | Observed | Reason |
|---|---|---|---|---|---|
| 1 | satisfied | `AR-175.1-20260907-8b217a39` | `d1dbc3748eaf6672d2223ca9eba78cd6a96a716767962f3fbabfe4a70989b469` | 2026-09-07 | agency_runtime/server/dashboard.py:1999-2080 returns schema_version agency.dashboard.control.v1 in both normal and restart-required control responses. |
| 2 | satisfied | `AR-175.2-20260907-fea43e9c` | `b6c1328b2595c653346f3b7f9c466eea0de511344be2f39bda64babdca32d2ec` | 2026-09-07 | dashboard-live.js guards application by schema and generation, while dashboard_ui.test.mjs and the focused green transcript demonstrate last-good state retention and no legacy fanout across 20 failure cases. |
| 3 | satisfied | `AR-175.3-20260907-8c4727fe` | `fafb9335c06c44b983a63a9aeb9ebe5d326e794f1414f8f58a4d672810b7f204` | 2026-09-07 | dashboard-live.js:2076-2201 suppresses abort, lifecycle and obsolete-generation failures, while dashboard_ui.test.mjs:4677-4754 asserts unchanged notices and fresh state for eight cancellation cases recorded as passing in the focused transcript. |
| 4 | satisfied | `AR-175.4-20260907-50e2f9bd` | `1627fbee6f8433da001d2ac9ccf30bd122af5bda9c21767b95e39f52e625266e` | 2026-09-07 | scripts/verify_dashboard_browser.mjs:127-190 covers 404 and wrong-schema faults with state-retention and zero legacy-request assertions; the cited loaded-browser transcript reports 36 passing fault cases. |
| 5 | satisfied | `AR-175.5-20260907-925ae671` | `594713e0a12726521d4d1ec4cfb519e7b0dd03f392cb1065639a5b43efa0593a` | 2026-09-07 | tests/test_release_packaging.py retains the strict 378-KiB assertion, and the cited Asset gate transcript records passing tests with 386,965 bytes against the unchanged 387,072-byte ceiling. |
