---
title: "AR-360 acceptance verification record"
status: active
category: roadmap
created: 2026-09-02
updated: 2026-09-02
tags: [acceptance, verification]
related:
  - docs/roadmap/issue-AR-360-battery-pass-k-grading.md
supersedes: []
superseded_by: null
type: acceptance-verification
issue_id: AR-360
candidate_commit: 2a38945265dbd526617d445f3d85d1cc1140d113
evidence_cutoff: 2026-09-02
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/433
---

# AR-360 acceptance verification record

Battery pass^k / pass@k grading: builder evidence cited by the integrator against the merged
candidate `2a389452`; every verdict below comes from one isolated
single-check verifier run (`scripts/verify_acceptance.py`, codex transport)
that saw only that criterion and its own rows.

## Builder evidence

| Criterion | Kind | Artifact | Observed | Source |
|---|---|---|---|---|
| 1 | test | `test_trial_count_is_bounded_and_grading_modes_follow_the_probe` | 2026-09-01 | `tests/test_harness_battery.py:708-721` |
| 1 | file | `probe_grading_mode` | 2026-09-01 | `agency_runtime/core/harness_battery.py:507-515` |
| 1 | test | `test_flaky_canary_probe_fails_under_pass_all_k_and_names_the_failing_trial` | 2026-09-01 | `tests/test_harness_battery.py:797-858` |
| 1 | test | `test_flaky_ordinary_probe_passes_under_pass_any_k_and_records_every_trial` | 2026-09-01 | `tests/test_harness_battery.py:733-794` |
| 2 | test | `test_flaky_ordinary_probe_passes_under_pass_any_k_and_records_every_trial` | 2026-09-01 | `tests/test_harness_battery.py:733-794` |
| 2 | file | `_run_graded_probe` | 2026-09-01 | `agency_runtime/core/harness_battery.py:566-604` |
| 2 | test | `test_flaky_canary_probe_fails_under_pass_all_k_and_names_the_failing_trial` | 2026-09-01 | `tests/test_harness_battery.py:797-858` |
| 2 | test | `test_run_battery_gates_on_change_updates_proof_and_seals_receipts` | 2026-09-01 | `tests/test_harness_battery.py:375-449` |
| 2 | file | `_fingerprint_entry` | 2026-09-01 | `agency_runtime/core/harness_battery.py:662-692` |
| 3 | test | `test_flaky_ordinary_probe_passes_under_pass_any_k_and_records_every_trial` | 2026-09-01 | `tests/test_harness_battery.py:733-794` |
| 3 | test | `test_flaky_canary_probe_fails_under_pass_all_k_and_names_the_failing_trial` | 2026-09-01 | `tests/test_harness_battery.py:797-858` |
| 3 | test | `test_grade_trials_folds_outcomes_per_mode` | 2026-09-01 | `tests/test_harness_battery.py:676-705` |

## Verification

| Criterion | Verdict | Verifier run | Evidence digest | Observed | Reason |
|---|---|---|---|---|---|
| 1 | satisfied | `AR-360.1-20260902-f83b2f87` | `41fe57fdf970ac7c2018888abc90266561c21497d175ee41a9bef81c6b083cad` | 2026-09-02 | The excerpts show probe_grading_mode maps canary hosts to pass_all_k and ordinary hosts to pass_any_k, with tests verifying pass^k failure identifies trial 1 and pass@k success records both trials. |
| 2 | satisfied | `AR-360.2-20260902-2d700480` | `90c064f7e5970201044df922c6a58fc39e7ba17211d961ab802f6b96ce6ccfab` | 2026-09-02 | The cited tests assert all trial outcomes in host detail and sealed receipts and assert fingerprint last_trials counts, while _run_graded_probe records each executed trial and _fingerprint_entry persists its summary. |
| 3 | satisfied | `AR-360.3-20260902-23ee5e56` | `ad91b03fae7259ae1b96991d5a838ff6198331b12df46086b00ee0bc88178390` | 2026-09-02 | The cited tests show an alternating failed/passed two-trial series passing under pass_any_k, failing under pass_all_k with trial 1 identified, and direct grade_trials assertions for both modes. |
