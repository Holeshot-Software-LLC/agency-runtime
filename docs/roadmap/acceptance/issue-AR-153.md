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

No verdicts supplied yet; the isolated runner owns this table. Criterion 4 is
explicitly reconciled with ADR-0105; the issue preserves its historical wording.

| Criterion | Verdict | Verifier run | Evidence digest | Observed | Reason |
|---|---|---|---|---|---|
