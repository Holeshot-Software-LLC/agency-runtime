---
title: "AR-138 acceptance verification record"
status: active
category: roadmap
created: 2026-09-07
updated: 2026-09-07
tags: [acceptance, verification, dashboard, accessibility]
related:
  - docs/roadmap/issue-AR-138-coherent-observable-dashboard-ui.md
  - docs/roadmap/acceptance/evidence/AR-138-current-dashboard-20260907.md
supersedes: []
superseded_by: null
type: acceptance-verification
issue_id: AR-138
candidate_commit: fa4d042bf0260db4fd6c4ec16606740f5c3a7847
evidence_cutoff: 2026-09-07
tracker_url: null
---

# AR-138 acceptance verification record

## Builder evidence

| Criterion | Kind | Artifact | Observed | Source |
|---|---|---|---|---|
| 1 | file | Control and full refresh reject stale generations and aborted/replaced controllers before committing | 2026-09-07 | agency_runtime/dashboard/dashboard-live.js:2068-2208 |
| 1 | test | Deferred live and full refresh responses cannot overwrite newer generations | 2026-09-07 | tests/dashboard_ui.test.mjs:4277-4349 |
| 1 | test | View-scoped intent wins deferred races with control and full refresh | 2026-09-07 | tests/dashboard_ui.test.mjs:4601-4729 |
| 1 | command-output | All 142 UI tests pass, including the deferred-response cases | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-138-current-dashboard-20260907.md#current-verification |
| 2 | file | Failed control refresh retains the last revision and exposes a stale state and request ID | 2026-09-07 | agency_runtime/dashboard/dashboard-live.js:2008-2115 |
| 2 | test | Missing or unsupported control responses do not replace last-good state | 2026-09-07 | tests/dashboard_ui.test.mjs:4446-4468 |
| 2 | file | Browser abort injection requires retained revision, visible stale notice and successful recovery | 2026-09-07 | scripts/verify_dashboard_browser.mjs:112-129 |
| 2 | command-output | Three viewports pass the actual control failure/recovery assertions | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-138-current-dashboard-20260907.md#browser-evidence |
| 3 | file | One server response binds configuration, roster generation, governance, hosts, master state and control revision | 2026-09-07 | agency_runtime/server/dashboard.py:1999-2077 |
| 3 | file | The client validates and completes revision-bound collections before applying one control snapshot | 2026-09-07 | agency_runtime/dashboard/dashboard-live.js:1963-2010 |
| 3 | test | Initial refresh and control polling consume the single control snapshot with declared revisions | 2026-09-07 | tests/dashboard_ui.test.mjs:4350-4444 |
| 3 | command-output | UI suite passes 142 and dashboard API/auth/transaction modules pass 180 | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-138-current-dashboard-20260907.md#current-verification |
| 4 | file | Interaction descriptors preserve and restore focus, text selection and open disclosures around rendering | 2026-09-07 | agency_runtime/dashboard/dashboard-core.js:440-490 |
| 4 | test | Configuration controls preserve dirty edits across refresh | 2026-09-07 | tests/dashboard_ui.test.mjs:1875-1950 |
| 4 | file | Browser check requires a real control poll and compares focused field, selection, value and all open settings details | 2026-09-07 | scripts/verify_dashboard_browser.mjs:86-108 |
| 4 | command-output | All three viewport interaction checks pass against the installed wheel | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-138-current-dashboard-20260907.md#browser-evidence |
| 5 | file | Real browser checks seven loaded views at desktop, intermediate and 375 px widths with axe and geometry assertions | 2026-09-07 | scripts/verify_dashboard_browser.mjs:30-84 |
| 5 | file | The test fixture requires the installed package identity and denies server outbound calls while serving real wheel assets | 2026-09-07 | scripts/verify_dashboard_browser.py:21-94 |
| 5 | test | Four focused regressions cover named focusable scroll regions, wrapping metrics, text contrast and semantic groups | 2026-09-07 | tests/dashboard_ui.test.mjs:3245-3287 |
| 5 | command-output | Twenty-one loaded browser checks pass with zero axe violations, zero page overflow and zero clipped metrics; exact versions, hashes, screenshots and limitations are recorded | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-138-current-dashboard-20260907.md#browser-evidence |
| 6 | file | Fetch, HTTP and correlation errors log the generated UUIDv4 and return it through the safe API error | 2026-09-07 | agency_runtime/dashboard/dashboard-core.js:338-402 |
| 6 | test | Invalid response correlation and malformed errors cannot substitute unsafe IDs | 2026-09-07 | tests/dashboard_ui.test.mjs:755-903 |
| 6 | file | Real browser network failure requires the same safe UUID in notice and application console | 2026-09-07 | scripts/verify_dashboard_browser.mjs:112-129 |
| 6 | command-output | Three injected network failures each produce a correlated safe request ID and recover; unplanned console/HTTP errors are zero | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-138-current-dashboard-20260907.md#browser-evidence |

## Verification

The isolated runner supplied all six rows below. Criterion 1 is contradicted:
a replaced full refresh can apply a late error to newer connection state. Five
criteria are satisfied. Preserve this complete first review before repairing
the remaining race and freezing a new candidate; no verdict is relabeled.

| Criterion | Verdict | Verifier run | Evidence digest | Observed | Reason |
|---|---|---|---|---|---|
| 1 | contradicted | `AR-138.1-20260907-a5bc06ef` | `92bce40266bd2aa17d231110077611bd1212926e9e2dbe8e4f15242b6b0ca6d1` | 2026-09-07 | dashboard-live.js:2068-2187 guards successful full-refresh responses but not its catch path, so a replaced request's late non-AbortError can overwrite newer connection state with Unavailable. |
| 2 | satisfied | `AR-138.2-20260907-8c857f24` | `f3c3c70d864e969178b4bf151c334c8b369a222b1866384fa91530a480e335a6` | 2026-09-07 | dashboard-live.js marks failed control refreshes stale and displays a failure notice, dashboard_ui.test.mjs checks retained state and staleness, and the browser evidence records visible failure and recovery at three viewports. |
| 3 | satisfied | `AR-138.3-20260907-7f391d96` | `5574cf5abd450c9c39f48512b234c9096769c02ba4ff40e9658d7e5a5cace13c` | 2026-09-07 | dashboard.py:1999-2077 binds related control data under one control_revision, and dashboard_ui.test.mjs:4350-4444 shows initial and polling refreshes update related panels from the single /api/control response. |
| 4 | satisfied | `AR-138.4-20260907-99702c9a` | `4f1db4a75d5be08a4505642e1626fc0ebbabca3a899f757eed52222f07c1b85a` | 2026-09-07 | dashboard-core.js captures and restores focus, selection and open details; verify_dashboard_browser.mjs asserts preservation across a real control poll, and the browser evidence records passes at all three viewports. |
| 5 | satisfied | `AR-138.5-20260907-e45df73d` | `08bb9dbe466a137a4d15f8b78420e008631442867e57bf0029ee354a0cc84778` | 2026-09-07 | AR-138-current-dashboard-20260907.md records exit 0 and 21 passing browser checks, including desktop and 375 px widths with zero axe violations, overflow or clipped metrics; verify_dashboard_browser.mjs shows the corresponding automated assertions. |
| 6 | satisfied | `AR-138.6-20260907-b8fa4ebe` | `216b4a1e33a2f6bf80beeb57156bcc16a5e81ef988e29e12f5325cf9f5f93313` | 2026-09-07 | dashboard-core.js validates UUIDv4 IDs and includes them in console logs and API errors; browser checker assertions and recorded browser evidence show matching safe IDs in failure notices and console output. |
