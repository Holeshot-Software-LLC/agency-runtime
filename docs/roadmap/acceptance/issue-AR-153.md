---
title: "AR-153 acceptance verification record"
status: active
category: roadmap
created: 2026-09-07
updated: 2026-09-07
tags: [acceptance, verification, dashboard, workforce]
related:
  - docs/roadmap/issue-AR-153-complete-worker-detail-evidence.md
  - docs/roadmap/acceptance/evidence/AR-153-worker-detail-20260907.md
  - docs/decisions/0105-bound-delivery-to-live-demo-checkpoints.md
supersedes: []
superseded_by: null
type: acceptance-verification
issue_id: AR-153
candidate_commit: ea57728532d99b5da0da60c7c6cec4dfa340fdba
evidence_cutoff: 2026-09-07
tracker_url: null
---

# AR-153 acceptance verification record

## Builder evidence

| Criterion | Kind | Artifact | Observed | Source |
|---|---|---|---|---|
| 1 | file | Worker identity predicates constrain both case count and ordered limited selection | 2026-09-07 | agency_runtime/core/store/workforce.py:2034-2066 |
| 1 | test | Three newer unrelated cases do not hide the target case at evidence limit one | 2026-09-07 | tests/test_workforce_lifecycle.py:517-545 |
| 1 | command-output | Fresh worker-detail and complete workforce-lifecycle suites pass | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-153-worker-detail-20260907.md#fresh-focused-checks |
| 2 | file | Evidence limit is validated and lineage selection uses the bounded limit with a matching total query | 2026-09-07 | agency_runtime/core/store/workforce.py:1895-1978 |
| 2 | file | HTTP collection page cap and serialized worker-detail response budget | 2026-09-07 | agency_runtime/server/dashboard.py:180-186 |
| 2 | file | Worker endpoint requests summary history and enforces its response budget | 2026-09-07 | agency_runtime/server/dashboard.py:2182-2270 |
| 2 | test | Lineage returns the limited page and exact total, excluding orphan versions | 2026-09-07 | tests/test_workforce_lifecycle.py:547-602 |
| 2 | test | Oversized worker response fails generically without exposing the private sentinel | 2026-09-07 | tests/test_dashboard.py:1347-1382 |
| 2 | command-output | Fresh focused checks pass; materialization bounds are not a constant-time aggregate-count claim | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-153-worker-detail-20260907.md#current-implementation |
| 3 | file | Returned rows, exact totals and truncation flags share one completed Store read transaction | 2026-09-07 | agency_runtime/core/store/workforce.py:2034-2088 |
| 3 | test | Concurrent worker mutation cannot mix worker identity with newer evidence | 2026-09-07 | tests/test_workforce_lifecycle.py:605-675 |
| 3 | test | HTTP summary preserves exact counts and readiness while omitting private documents | 2026-09-07 | tests/test_dashboard.py:1312-1344 |
| 3 | file | Renderer displays delivered records, exact shown-of-total labels and unavailable malformed totals | 2026-09-07 | agency_runtime/dashboard/dashboard-render.js:2139-2171 |
| 3 | test | UI assertions cover loaded lineage/hiring records, exact truncation labels and malformed count fallback | 2026-09-07 | tests/dashboard_ui.test.mjs:1286-1333 |
| 3 | command-output | Current Store/HTTP regressions and complete UI tests pass | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-153-worker-detail-20260907.md#fresh-focused-checks |
| 4 | command-output | Six focused Store/HTTP cases, complete 25-test workforce lifecycle and 176-test UI suite pass | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-153-worker-detail-20260907.md#fresh-focused-checks |
| 4 | command-output | Exact-byte reuse binds the 274-dashboard and 1085-pass/three-skip named warning-strict spine receipts | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-153-worker-detail-20260907.md#exact-byte-broader-evidence |
| 4 | command-output | Exact dashboard/spine command scope and passing results for unchanged source and tests | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-151-host-eligibility-20260907.md#final-current-verification |
| 4 | file | Governing bounded-delivery policy makes exhaustive corpus/matrix diagnostics optional | 2026-09-07 | docs/decisions/0105-bound-delivery-to-live-demo-checkpoints.md#decision |

## Verification

The isolated runner supplied all four verdicts below. Criterion 4 is
explicitly reconciled with ADR-0105; the issue preserves its historical wording.

| Criterion | Verdict | Verifier run | Evidence digest | Observed | Reason |
|---|---|---|---|---|---|
| 1 | satisfied | `AR-153.1-20260907-2cb1f5f8` | `81f46eda278e863e89386d32e99c708383c85d68964aa8007858ed2dd0144ce8` | 2026-09-07 | workforce.py applies worker identity predicates before ORDER BY and LIMIT; test_workforce_lifecycle.py verifies that three newer unrelated cases cannot hide the target case when evidence_limit is one. |
| 2 | satisfied | `AR-153.2-20260907-46266bbb` | `e9ca494b438481d95c35ac6e01639de90a118daf1be65894223043ca7814b8ec` | 2026-09-07 | workforce.py:1895-1978 validates and limits lineage retrieval; dashboard.py:2182-2270 applies a 2 MiB response budget, with lineage truncation and oversized-response behavior covered by the cited tests. |
| 3 | satisfied | `AR-153.3-20260907-90ddf430` | `b774efc8b6a53f20dbe052eece9f3fb9269644891b3c4d6cd00a71444b87ce37` | 2026-09-07 | workforce.py derives truncation from totals and returned rows; test_dashboard.py asserts HTTP count parity; dashboard-render.js and dashboard_ui.test.mjs demonstrate matching records, bounded labels, and malformed-total handling. |
| 4 | satisfied | `AR-153.4-20260907-09a3aca5` | `7bece28dc9d452b0d24cf84bb0fc48138e8460dc5c98591f024bc03a24f883b8` | 2026-09-07 | AR-153’s focused-check receipts show 6 focused, 25 Store and 176 UI tests passing; its exact-byte reuse of AR-151’s verification records 274 dashboard passes and 1,085 named warning-strict spine passes with three existing skips. |
