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

Pending the isolated single-criterion runner. The builder has recorded evidence,
not verdicts.

| Criterion | Verdict | Verifier run | Evidence digest | Observed | Reason |
|---|---|---|---|---|---|
