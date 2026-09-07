---
title: "AR-138 acceptance verification record"
status: active
category: roadmap
created: 2026-09-07
updated: 2026-09-07
tags: [acceptance, verification, dashboard, accessibility]
related:
  - docs/roadmap/issue-AR-138-coherent-observable-dashboard-ui.md
  - docs/roadmap/acceptance/evidence/AR-138-repaired-dashboard-20260907.md
supersedes: []
superseded_by: null
type: acceptance-verification
issue_id: AR-138
candidate_commit: 2ecde1a5be3ac38aa7b7b970945fa8bd42e7fa73
evidence_cutoff: 2026-09-07
tracker_url: null
---

# AR-138 acceptance verification record

## Builder evidence

| Criterion | Kind | Artifact | Observed | Source |
|---|---|---|---|---|
| 1 | file | Control and full refresh reject stale generations and aborted/replaced controllers before committing | 2026-09-07 | agency_runtime/dashboard/dashboard-live.js:2076-2225 |
| 1 | test | Deferred live and full refresh responses cannot overwrite newer generations | 2026-09-07 | tests/dashboard_ui.test.mjs:4277-4349 |
| 1 | test | View-scoped intent wins deferred races with control and full refresh | 2026-09-07 | tests/dashboard_ui.test.mjs:4601-4729 |
| 1 | command-output | All 172 UI tests pass, including the deferred-response cases | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-138-repaired-dashboard-20260907.md#current-verification |
| 1 | file | Live polling drops obsolete failures before they reach retry or reconciliation handlers | 2026-09-07 | agency_runtime/dashboard/dashboard-live.js:1080-1110 |
| 1 | test | Thirty late-failure regressions cover full, live and control refresh, reconciliation, network/401/503 responses, and request/commit generations | 2026-09-07 | tests/dashboard_ui.test.mjs:7953-8036 |
| 2 | file | Failed control refresh retains the last revision and exposes a stale state and request ID | 2026-09-07 | agency_runtime/dashboard/dashboard-live.js:2016-2126 |
| 2 | test | Missing or unsupported control responses do not replace last-good state | 2026-09-07 | tests/dashboard_ui.test.mjs:4446-4468 |
| 2 | file | Browser abort injection requires retained revision, visible stale notice and successful recovery | 2026-09-07 | scripts/verify_dashboard_browser.mjs:112-129 |
| 2 | command-output | Three viewports pass the actual control failure/recovery assertions | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-138-repaired-dashboard-20260907.md#browser-evidence |
| 3 | file | One server response binds configuration, roster generation, governance, hosts, master state and control revision | 2026-09-07 | agency_runtime/server/dashboard.py:1999-2077 |
| 3 | file | The client validates and completes revision-bound collections before applying one control snapshot | 2026-09-07 | agency_runtime/dashboard/dashboard-live.js:1971-2018 |
| 3 | test | Initial refresh and control polling consume the single control snapshot with declared revisions | 2026-09-07 | tests/dashboard_ui.test.mjs:4350-4444 |
| 3 | command-output | UI suite passes 172 and dashboard API/auth/transaction modules pass 180 | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-138-repaired-dashboard-20260907.md#current-verification |
| 4 | file | Interaction descriptors preserve and restore focus, text selection and open disclosures around rendering | 2026-09-07 | agency_runtime/dashboard/dashboard-core.js:440-490 |
| 4 | test | Configuration controls preserve dirty edits across refresh | 2026-09-07 | tests/dashboard_ui.test.mjs:1875-1950 |
| 4 | file | Browser check requires a real control poll and compares focused field, selection, value and all open settings details | 2026-09-07 | scripts/verify_dashboard_browser.mjs:86-108 |
| 4 | command-output | All three viewport interaction checks pass against the installed wheel | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-138-repaired-dashboard-20260907.md#browser-evidence |
| 5 | file | Real browser checks seven loaded views at desktop, intermediate and 375 px widths with axe and geometry assertions | 2026-09-07 | scripts/verify_dashboard_browser.mjs:30-84 |
| 5 | file | The test fixture requires the installed package identity and denies server outbound calls while serving real wheel assets | 2026-09-07 | scripts/verify_dashboard_browser.py:21-94 |
| 5 | test | Four focused regressions cover named focusable scroll regions, wrapping metrics, text contrast and semantic groups | 2026-09-07 | tests/dashboard_ui.test.mjs:3245-3287 |
| 5 | command-output | Twenty-one loaded browser checks pass with zero axe violations, zero page overflow and zero clipped metrics; exact versions, hashes, screenshots and limitations are recorded | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-138-repaired-dashboard-20260907.md#browser-evidence |
| 6 | file | Fetch, HTTP and correlation errors log the generated UUIDv4 and return it through the safe API error | 2026-09-07 | agency_runtime/dashboard/dashboard-core.js:338-402 |
| 6 | test | Invalid response correlation and malformed errors cannot substitute unsafe IDs | 2026-09-07 | tests/dashboard_ui.test.mjs:755-903 |
| 6 | file | Real browser network failure requires the same safe UUID in notice and application console | 2026-09-07 | scripts/verify_dashboard_browser.mjs:112-129 |
| 6 | command-output | Three injected network failures each produce a correlated safe request ID and recover; unplanned console/HTTP errors are zero | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-138-repaired-dashboard-20260907.md#browser-evidence |

## Verification

The complete first review is preserved verbatim at 25b9a67a. The isolated
runner supplied all six satisfied verdicts below for repaired candidate 2ecde1a5.

| Criterion | Verdict | Verifier run | Evidence digest | Observed | Reason |
|---|---|---|---|---|---|
| 1 | satisfied | `AR-138.1-20260907-99e8121c` | `35871ca361514a83d2e0a18c77f14dcd4ab0979c0deb342019426d7bbab16cd8` | 2026-09-07 | Generation and controller guards in dashboard-live.js reject obsolete responses, while deferred-race and late-failure tests in dashboard_ui.test.mjs assert newer state remains intact. |
| 2 | satisfied | `AR-138.2-20260907-7f979c9e` | `cf4af7b855bc50b84e753fa358e5f73564036beceb47fba1e27cb9d464ee0c36` | 2026-09-07 | dashboard-live.js marks failed control refreshes stale and displays a failure notice; dashboard_ui.test.mjs verifies retained state, and the browser evidence records visible staleness and recovery at three viewports. |
| 3 | satisfied | `AR-138.3-20260907-847c4d0b` | `93fbe2611d3306cf7739837110b530d7172e3216e9b7ffa98f4d00a0153146a6` | 2026-09-07 | dashboard.py:1999-2077 declares one control_revision for configuration, hosts, master, roster, and governance; dashboard_ui.test.mjs:4350-4444 verifies initial refresh and control polling populate related panels from that single response. |
| 4 | satisfied | `AR-138.4-20260907-290c38af` | `cb4e1ae37cbac13b9eec80dce55cda5a3bfee2a5b643190c68717694546622b2` | 2026-09-07 | dashboard-core.js captures and restores focus, selection and open details; verify_dashboard_browser.mjs asserts preservation across a real poll, and the browser evidence records passes at all three viewports. |
| 5 | satisfied | `AR-138.5-20260907-b9d04ce0` | `1960e1d26b95becb0238e9dbae467019c0f1b9d5508a9fb4898b762a81cf95d7` | 2026-09-07 | The browser evidence receipt records exit 0 and passed=true for 21 loaded-view checks at 1280, 1024 and 375 px, with zero axe violations, overflow or clipped metrics; the cited browser script implements those assertions. |
| 6 | satisfied | `AR-138.6-20260907-e5f16c1f` | `210011be341493b63f469bb0c0c752ce22d12c61bf8173d2be1874b0cd0e2cc9` | 2026-09-07 | dashboard-core.js validates UUIDv4 IDs and logs them on network and HTTP failures; verify_dashboard_browser.mjs checks the same ID in the UI notice and console, and the browser evidence records three correlated failures. |
