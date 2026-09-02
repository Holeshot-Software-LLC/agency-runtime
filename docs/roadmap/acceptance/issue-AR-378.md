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
candidate_commit: pending
evidence_cutoff: 2026-09-02
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/552
---

# AR-378 acceptance verification record

Pending draft. Builder evidence for the hiring failure receipt, cited against
the working tree; the record freezes to the implementation commit once that
commit is an ancestor of `HEAD`, and verification rows are written only then.

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
