---
title: "AR-378 acceptance verification record"
status: active
category: roadmap
created: 2026-09-02
updated: 2026-09-02
tags: [acceptance, verification]
related:
  - docs/roadmap/issue-AR-378-hiring-failure-records-no-attempt.md
supersedes: []
superseded_by: null
type: acceptance-verification
issue_id: AR-378
candidate_commit: 9ce98b3b8ef30a93aa5c13d2feb7ab34c3ddab10
evidence_cutoff: 2026-09-02
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/552
---

# AR-378 acceptance verification record

Builder evidence for the hiring failure receipt, cited against the AR-378
implementation commit `9ce98b3b`; every verdict below comes from one isolated
single-check verifier run (`scripts/verify_acceptance.py`) that saw only that
criterion and its own builder rows.

## Builder evidence

| Criterion | Kind | Artifact | Observed | Source |
|---|---|---|---|---|
| 1 | file | `HiringInferenceAttempt carries reason_code and latency_ms` | 2026-09-02 | `agency_runtime/core/workforce/hiring.py:522-536` |
| 1 | file | `_failed_attempt records stage, provider, requested model, status, reason code and latency` | 2026-09-02 | `agency_runtime/core/workforce/hiring.py:711-744` |
| 1 | file | `_invoke returns (result, applied, failures) and classifies each try it witnessed` | 2026-09-02 | `agency_runtime/core/workforce/hiring.py:747-818` |
| 1 | test | `test_failed_hiring_call_records_the_provider_model_and_latency` | 2026-09-02 | `tests/test_workforce_dynamic_hiring.py:2675-2702` |
| 1 | test | `test_call_that_reaches_its_deadline_is_recorded_as_a_timeout` | 2026-09-02 | `tests/test_workforce_dynamic_hiring.py:2705-2723` |
| 1 | command-output | `a failing hiring call prints one attempt with provider, requested_model, latency_ms and reason_code provider_call_failed` | 2026-09-02 | `docs/roadmap/acceptance/evidence/AR-378-evidence-20260902.txt:17-25` |
| 2 | file | `_failure_reason_codes names each failure class once, behind the stable stage code` | 2026-09-02 | `agency_runtime/core/workforce/hiring.py:821-833` |
| 2 | file | `the hiring abstention carries the failure class and its attempts` | 2026-09-02 | `agency_runtime/core/workforce/hiring.py:2178-2183` |
| 2 | test | `test_failed_critic_call_names_its_failure_class` | 2026-09-02 | `tests/test_workforce_dynamic_hiring.py:2726-2751` |
| 2 | command-output | `reason_codes = ('hiring_inference_failed', 'provider_call_failed') with one attempt behind it` | 2026-09-02 | `docs/roadmap/acceptance/evidence/AR-378-evidence-20260902.txt:20-25` |
| 3 | test | `test_failed_hiring_call_records_the_provider_model_and_latency asserts a non-empty attempts tuple` | 2026-09-02 | `tests/test_workforce_dynamic_hiring.py:2675-2702` |
| 3 | test | `test_oversized_hiring_prompt_is_refused_before_any_provider_call` | 2026-09-02 | `tests/test_workforce_dynamic_hiring.py:2754-2778` |
| 3 | test | `test_exhausted_call_budget_is_recorded_as_a_skipped_attempt` | 2026-09-02 | `tests/test_workforce_dynamic_hiring.py:2781-2804` |
| 3 | test | `test_durable_model_receipts_exclude_the_failed_attempt` | 2026-09-02 | `tests/test_workforce_dynamic_hiring.py:2807-2841` |
| 3 | test | `test_calls_used_excludes_attempts_that_never_spent_a_call` | 2026-09-02 | `tests/test_workforce_dynamic_hiring.py:2844-2864` |
| 3 | command-output | `all seven AR-378 cases PASSED under -W error` | 2026-09-02 | `docs/roadmap/acceptance/evidence/AR-378-evidence-20260902.txt:3-16` |

## Verification

| Criterion | Verdict | Verifier run | Evidence digest | Observed | Reason |
|---|---|---|---|---|---|
| 1 | satisfied | `AR-378.1-20260902-890d71bf` | `0a59c2921cb225bb78ff1d63ba6f3fc5bb5d1b8175660c8979425eba6cb3c261` | 2026-09-02 | The cited implementation and test show one failed hiring attempt records provider, requested_model, latency_ms, and the distinguishable reason_code provider_call_failed, with timeout separately classified as provider_call_timed_out. |
| 2 | satisfied | `AR-378.2-20260902-c729c549` | `54eab7d0a55e9e447193c279a1fab15abf8816ab6f0181b91b8056b4c80265b0` | 2026-09-02 | The cited command output shows an abstention with reason_codes ('hiring_inference_failed', 'provider_call_failed') in that order and exactly one failed hiring attempt carrying provider_call_failed. |
| 3 | satisfied | `AR-378.3-20260902-dee9e358` | `342c8e9184a2cec3384140fa3cbc1a3ea5c679c3686be239be6d9e372673aad1` | 2026-09-02 | The cited test excerpts pin a non-empty failed-provider attempt, both skip classes, applied-only durable receipts, and calls_used, while the pytest artifact shows the seven targeted AR-378 cases passed under -W error. |
