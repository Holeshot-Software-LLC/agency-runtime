---
title: "AR-413 acceptance verification record"
status: active
category: roadmap
created: 2026-09-08
updated: 2026-09-08
tags: [acceptance, verification, workforce, receipts]
related:
  - docs/roadmap/issue-AR-413-preserve-http-status-in-staffing-receipts.md
  - docs/roadmap/acceptance/evidence/AR-413-installed-http-status-20260908.md
supersedes: []
superseded_by: null
type: acceptance-verification
issue_id: AR-413
candidate_commit: 65a387ede933ed0b8cca5cc2d7816c4d414eba16
evidence_cutoff: 2026-09-08
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/765
---

# AR-413 acceptance verification record

## Builder evidence

Observations concern exact-status preservation, not native staffing reliability.

| Criterion | Kind | Artifact | Observed | Source |
|---|---|---|---|---|
| 1 | test | Four transport statuses through full failed workforce and SQLite | 2026-09-08 | tests/test_staffing_http_status.py:20-53 |
| 1 | command-output | Focused 80-pass run and its scope | 2026-09-08 | docs/roadmap/acceptance/evidence/AR-413-installed-http-status-20260908.md#source-and-focused-checks |
| 2 | test | Operator, terminal and preflight fixed points retain each status | 2026-09-08 | tests/test_staffing_http_status.py:20-53 |
| 2 | test | Hiring failures retain status through receipt and preflight projection | 2026-09-08 | tests/test_staffing_http_status.py:77-99 |
| 2 | test | Unknown and legacy status values remain absent | 2026-09-08 | tests/test_staffing_http_status.py:56-76 |
| 2 | test | Actual timeout/network failures omit status through workforce, SQLite, hiring and all projections; absent-field legacy fixed points | 2026-09-08 | tests/test_staffing_http_status.py:102-144 |
| 3 | test | Private body, key, headers and endpoint excluded from projections and Store | 2026-09-08 | tests/test_staffing_http_status.py:20-53 |
| 3 | test | Invalid types and unbounded integers do not become evidence | 2026-09-08 | tests/test_staffing_http_status.py:56-76 |
| 4 | command-output | Verified canonical wheel, isolated import, four real loopback responses and SQLite readback | 2026-09-08 | docs/roadmap/acceptance/evidence/AR-413-installed-http-status-20260908.md#installed-failure-demonstration |
| 4 | command-output | Unchanged provider and native policy scope | 2026-09-08 | docs/roadmap/acceptance/evidence/AR-413-installed-http-status-20260908.md#source-and-focused-checks |

## Verification

| Criterion | Verdict | Verifier run | Evidence digest | Observed | Reason |
|---|---|---|---|---|---|
| 1 | satisfied | `AR-413.1-20260908-7a27b998` | `53427f79eb700bff2d5ed496b2e18e343117c7c469eaa086fc63fad1c770d575` | 2026-09-08 | The four-status parametrized test in tests/test_staffing_http_status.py asserts failed-turn and persisted receipt status equality; the cited evidence document records passing checks and SQLite readback of 401, 408, 429, and 502. |
| 2 | satisfied | `AR-413.2-20260908-1789bab2` | `ac2f5753e5733cd80b414d62ad3c1e7394c3b7f67f972de33a1066dce3bb6d19` | 2026-09-08 | tests/test_staffing_http_status.py:20-144 demonstrates status retention in routing/operator projections and hiring receipts, and omission for invalid, unknown, non-HTTP and legacy outcomes. |
| 3 | satisfied | `AR-413.3-20260908-6429c77d` | `05204b881c2c84241c1e33e291a106ec2248a74f7b66189f97edd69f4d247c0c` | 2026-09-08 | tests/test_staffing_http_status.py:20-76 checks that all three projections omit malformed and unbounded statuses and exclude injected secrets, responses, headers and endpoints, including from persisted receipts. |
| 4 | satisfied | `AR-413.4-20260908-556cfeb8` | `417a592940daf7c81924d7041ec70f5b07bd917c4f3b1ad107d7d6895d4a6f99` | 2026-09-08 | AR-413-installed-http-status-20260908.md records isolated installed loopback failures with SQLite statuses 401, 408, 429 and 502, no gateway log inference, and unchanged provider selection and native policy. |
