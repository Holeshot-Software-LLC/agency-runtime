---
title: "AR-388 acceptance verification record"
status: active
category: roadmap
created: 2026-09-04
updated: 2026-09-04
tags: [acceptance, verification]
related:
  - docs/roadmap/issue-AR-388-unset-credential-reads-as-provider-unavailable.md
  - docs/decisions/0204-name-the-credential-the-launching-environment-never-carried.md
supersedes: []
superseded_by: null
type: acceptance-verification
issue_id: AR-388
candidate_commit: pending
evidence_cutoff: 2026-09-04
tracker_url: null
---

# AR-388 acceptance verification record

Pending draft. A routed inference install is declared inference in any
environment; the structured transport answers `provider_credential_env_unset`
for a provider whose credential variable the launching environment lacks
instead of calling, and the stage records it with no budget spent; the
failure outcome, the preflight receipt and the fail-open disclosure carry
`workforce_credential_env_unset`; and `agency doctor` warns by variable name,
listing the routed profiles, when the variable is unset in the inspected
environment. Criteria 2 to 4 are also evidenced on the installed configuration
against a read-only copy of the installed store.

## Builder evidence

| Criterion | Kind | Artifact | Observed | Source |
|---|---|---|---|---|
| 1 | file | `_inference_declared counts a resolved workforce.planner or workforce.recruiter route as declared inference beside the legacy providers chain and the judge, whose credential is borrowed from the environment` | 2026-09-04 | `agency_runtime/core/workforce/inference.py:3674-3693` |
| 1 | file | `plan_and_staff_workforce asks _inference_declared with the turn's host so harness-scoped routes count` | 2026-09-04 | `agency_runtime/core/workforce/inference.py:4109-4117` |
| 1 | test | `test_a_routed_install_is_declared_inference_without_a_legacy_key asserts the routed install is declared with the variable unset and an unconfigured install is not` | 2026-09-04 | `tests/test_credential_env_unset.py:81-88` |
| 1 | command-output | `the installed runtime read the same routed install as undeclared without the key and declared with it; the branch runtime reads it as declared without the key` | 2026-09-04 | `docs/roadmap/acceptance/evidence/AR-388-evidence-20260904.txt:29-34` |
| 2 | file | `the structured transport answers a provider with an api_key_env, no direct key, on a keyed adapter, whose variable the environment lacks, with a result whose failure_reason is provider_credential_env_unset and makes no request; cli, ollama and keyless loopback are not faults` | 2026-09-04 | `agency_runtime/core/structured_provider.py:531-569` |
| 2 | file | `invoke_structured_provider_result asks before resolving the key or building a request` | 2026-09-04 | `agency_runtime/core/structured_provider.py:651-652` |
| 2 | file | `StructuredProviderResult.failure_reason: a non-empty value means the transport made no call and says why` | 2026-09-04 | `agency_runtime/core/structured_provider.py:120-122` |
| 2 | file | `the stage loop records the transport's answer as a failed attempt, returns the reserved call budget, moves to the next provider, and fails the stage as workforce_provider_unavailable when no provider was called` | 2026-09-04 | `agency_runtime/core/workforce/inference.py:1543-1558` |
| 2 | file | `_CallBudget.release returns one unit for an attempt the transport never made` | 2026-09-04 | `agency_runtime/core/workforce/inference.py:1035-1039` |
| 2 | file | `_inference_failure appends workforce_credential_env_unset when an attempt carries the credential code, keeps the status inference_unavailable, and puts the code on the empty staffing decision's abstention reasons` | 2026-09-04 | `agency_runtime/core/workforce/inference.py:3710-3742` |
| 2 | test | `test_the_transport_refuses_to_call_without_the_variable, test_the_unset_variable_is_recorded_before_any_call and test_with_the_variable_set_the_transport_calls_the_provider pin the transport's answer, the attempt, zero calls used, the abstention codes and the staffing reasons without the variable, and the ordinary call with budget spent once it is set` | 2026-09-04 | `tests/test_credential_env_unset.py:91-163` |
| 2 | test | `test_only_a_declared_variable_on_a_keyed_adapter_is_a_credential_fault pins keyless loopback, a direct key, cli and ollama as non-faults` | 2026-09-04 | `tests/test_credential_env_unset.py:193-219` |
| 3 | file | `project_preflight_provider_attempts keeps the attempt's stage and reason code family on the receipt` | 2026-09-04 | `agency_runtime/core/preflight_failure.py:228-280` |
| 3 | file | `preflight_staffing_reason_codes projects the staffing decision's abstention reason codes onto the receipt` | 2026-09-04 | `agency_runtime/core/preflight_failure.py:318-327` |
| 3 | file | `render_fail_open_disclosure renders the bounded reason class with the staffing codes inside the 512-character line` | 2026-09-04 | `agency_runtime/core/fail_open_disclosure.py:81-125` |
| 3 | test | `test_receipt_and_disclosure_name_the_unset_credential projects the outcome onto the receipt attempts and staffing codes and renders the disclosure line naming workforce_credential_env_unset within budget` | 2026-09-04 | `tests/test_credential_env_unset.py:166-190` |
| 3 | command-output | `the branch runtime on the installed configuration and a 291-contract store copy without the key: one planner attempt provider_credential_env_unset, calls_used 0, the receipt projection and the disclosure line carry workforce_credential_env_unset` | 2026-09-04 | `docs/roadmap/acceptance/evidence/AR-388-evidence-20260904.txt:35-46` |
| 4 | file | `_routed_inference_profiles collects the profiles the routes, default profile and harness sections name` | 2026-09-04 | `agency_runtime/core/doctor.py:768-786` |
| 4 | file | `_inference_credential_checks emits one check per credential variable: warn naming the variable, the routed profiles and the remedy when unset in the inspected environment, pass when set; keyed adapters only` | 2026-09-04 | `agency_runtime/core/doctor.py:789-836` |
| 4 | file | `run_doctor includes the credential checks after the provider chain checks` | 2026-09-04 | `agency_runtime/core/doctor.py:972-972` |
| 4 | test | `test_doctor_names_the_unset_variable_and_the_routed_profiles pins the warn, the profile list, the remedy, the pass and the empty case` | 2026-09-04 | `tests/test_credential_env_unset.py:222-238` |
| 4 | command-output | `agency doctor --json from the branch runtime on the installed configuration: warn naming LITELLM_API_KEY and the eight routed profiles without the key, pass with it` | 2026-09-04 | `docs/roadmap/acceptance/evidence/AR-388-evidence-20260904.txt:47-50` |

## Verification

| Criterion | Verdict | Verifier run | Evidence digest | Observed | Reason |
|---|---|---|---|---|---|
