---
title: "AR-352 acceptance verification record"
status: active
category: roadmap
created: 2026-09-02
updated: 2026-09-02
tags: [acceptance, verification]
related:
  - docs/roadmap/issue-AR-352-scope-battery-deltas-by-session.md
supersedes: []
superseded_by: null
type: acceptance-verification
issue_id: AR-352
candidate_commit: 2a38945265dbd526617d445f3d85d1cc1140d113
evidence_cutoff: 2026-09-02
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/416
---

# AR-352 acceptance verification record

Session-scoped battery deltas: builder evidence cited by the integrator against the merged
candidate `2a389452`; every verdict below comes from one isolated
single-check verifier run (`scripts/verify_acceptance.py`, codex transport)
that saw only that criterion and its own rows.

## Builder evidence

| Criterion | Kind | Artifact | Observed | Source |
|---|---|---|---|---|
| 1 | test | `test_ordinary_battery_ignores_foreign_session_preflight_failures` | 2026-09-01 | `tests/test_harness_battery.py:288-329` |
| 2 | test | `test_ordinary_battery_fails_on_its_own_sessions_preflight_failure` | 2026-09-01 | `tests/test_harness_battery.py:332-354` |
| 3 | test | `test_ordinary_battery_does_not_borrow_foreign_staffing_rows` | 2026-09-01 | `tests/test_harness_battery.py:357-372` |
| 3 | file | `_scope_activity_delta` | 2026-09-01 | `agency_runtime/core/harness_battery.py:412-445` |
| 4 | test | `test_ordinary_battery_ignores_foreign_session_preflight_failures` | 2026-09-01 | `tests/test_harness_battery.py:288-329` |
| 4 | test | `test_ordinary_battery_fails_on_its_own_sessions_preflight_failure` | 2026-09-01 | `tests/test_harness_battery.py:332-354` |
| 4 | test | `test_ordinary_battery_does_not_borrow_foreign_staffing_rows` | 2026-09-01 | `tests/test_harness_battery.py:357-372` |

## Verification

| Criterion | Verdict | Verifier run | Evidence digest | Observed | Reason |
|---|---|---|---|---|---|
| 1 | satisfied | `AR-352.1-20260902-253941b8` | `2b82ddc8ef962af11cbef61cc6c603739d806b30bc83d9c6de8725b5710143c2` | 2026-09-02 | The cited test excerpt constructs a staffed, finalized own turn with four foreign-session preflight failures, including the same host’s interactive session, and asserts the outcome is passed. |
| 2 | satisfied | `AR-352.2-20260902-68e5f9bf` | `cf1a9f7cbba3938ca2aa59a02038ecae7afd95f47843410a2cba731785ae635a` | 2026-09-02 | The cited test excerpt asserts that both a matching-session preflight failure and a trace-only own failure produce a failed battery outcome with one own-session preflight failure. |
| 3 | satisfied | `AR-352.3-20260902-a0858500` | `ec966ddd9bb86cc3da784f930261baf20561b9e6deb6f3f7602a2fca718d1804` | 2026-09-02 | The cited _scope_activity_delta excerpt returns separate own_sessions, own_session_row_counts, foreign_session_activity, and foreign_session_hosts fields, and the cited test asserts the latter three against mixed-session rows. |
| 4 | satisfied | `AR-352.4-20260902-5e0c07aa` | `cb97cce9327cb8a1aa543a8f640b0659f5c1e28ea7eb0dd26cdd33a1606c8cc8` | 2026-09-02 | The cited excerpts show all three named regression tests, covering ignored foreign failures, failure on own-session preflight errors, and rejection of foreign staffing rows. |
