---
title: "AR-392 acceptance verification record"
status: active
category: roadmap
created: 2026-09-04
updated: 2026-09-04
tags: [acceptance, verification]
related:
  - docs/roadmap/issue-AR-392-transport-failures-collapse-to-one-code.md
  - docs/decisions/0209-name-the-transport-cause-instead-of-one-code.md
supersedes: []
superseded_by: null
type: acceptance-verification
issue_id: AR-392
candidate_commit: 0ff7d390c806dbfaae94a970b80aa3cabdaaf223
evidence_cutoff: 2026-09-04
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/649
---

# AR-392 acceptance verification record

Verified on the first pass at `03e302a5`. The two stage loops classify an
identical transport failure identically and carry the elapsed time; a non-2xx
answer keeps its status instead of being discarded by the blanket `except`; a
complete body whose model text is not a JSON object is its own cause beside a
cut reply and a deadline abort, reproduced from the capture391 turn 206 shape;
`failure_reason` keeps one meaning while `call_attempted` decides whether the
call budget is spent; and `agency doctor` states each routed profile's
effective deadline, shown live on the installed configuration.

Criterion 5 and the transport classifications are evidenced against the
installed configuration read-only. No live gateway call was made and no
credential was required: every transport case is driven through the seam the
AR-385 suite already uses.

## Builder evidence

| Criterion | Kind | Artifact | Observed | Source |
|---|---|---|---|---|
| 1 | file | `_invoke_stage times the call from the outside and splits a bare None into provider_call_timed_out or provider_call_failed, both carrying latency_ms` | 2026-09-04 | `agency_runtime/core/workforce/inference.py:1710-1765` |
| 1 | file | `both stage loops read the two codes from reply_budget, so a code cannot be added to one half of the split and not the other` | 2026-09-04 | `agency_runtime/core/reply_budget.py:78-130` |
| 1 | file | `WorkforceInferenceAttempt carries timeout_ms beside latency_ms, and _attempt fills it from the provider's effective deadline` | 2026-09-04 | `agency_runtime/core/workforce/inference.py:764-770` |
| 1 | file | `HiringInferenceAttempt carries the same field, filled at both of its construction sites; it is deliberately absent from receipt_id, which identifies the call rather than the configuration around it` | 2026-09-04 | `agency_runtime/core/workforce/hiring.py:566-573` |
| 1 | file | `project_model_receipt_attempts carries both durations onto the durable receipt, added only when present so a route stored before this change still re-projects to itself` | 2026-09-04 | `agency_runtime/core/selector/receipt_projection.py:468-483` |
| 1 | test | `test_the_staffing_loop_splits_a_bare_none_the_way_the_hiring_loop_does drives both loops with one invoker and one clock and asserts the same code, the same latency and the same timeout_ms` | 2026-09-04 | `tests/test_transport_failure_causes.py:255-305` |
| 1 | test | `test_both_figures_reach_the_durable_receipt asserts the projection carries 30040 against 30000, and the two fixed-point tests pin that an attempt without durations still projects exactly as it did` | 2026-09-04 | `tests/test_transport_failure_causes.py:308-396` |
| 1 | command-output | `all 1289 attempts across the last 400 live receipts carried neither latency_ms nor timeout_ms before this change: the projection emitted eight fields and no duration` | 2026-09-04 | `docs/roadmap/acceptance/evidence/AR-392-evidence-20260904.txt:29-35` |
| 2 | file | `_transport_exception_cause classifies the HTTPError open_no_redirect re-raises and keeps its status; the blanket except stays blanket and anything unrecognised stays on the residual code` | 2026-09-04 | `agency_runtime/core/structured_provider.py:634-653` |
| 2 | file | `StructuredProviderResult.http_status carries the status onto the result and its receipt` | 2026-09-04 | `agency_runtime/core/structured_provider.py:136-142` |
| 2 | test | `test_a_non_2xx_status_is_recorded_instead_of_discarded pins 401, 429 and 502 with their statuses` | 2026-09-04 | `tests/test_transport_failure_causes.py:118-141` |
| 2 | test | `test_an_unrecognised_transport_exception_stays_on_the_residual_code pins that the blanket except is not narrowed` | 2026-09-04 | `tests/test_transport_failure_causes.py:159-172` |
| 2 | command-output | `a 429 reaches the result as provider_http_status_error with http_status 429` | 2026-09-04 | `docs/roadmap/acceptance/evidence/AR-392-evidence-20260904.txt:22-22` |
| 3 | file | `a complete body whose model text is not a JSON object returns provider_model_text_not_json; the truncated branch above it is untouched` | 2026-09-04 | `agency_runtime/core/structured_provider.py:800-808` |
| 3 | test | `test_the_misplaced_brace_from_capture391_turn_206_is_not_a_cut_reply builds the observed shape -- a candidate object closing before its score, finish_reason stop, well below the cap -- asserts json.loads rejects it, and pins the cause as distinct from both provider_response_truncated and provider_call_timed_out` | 2026-09-04 | `tests/test_transport_failure_causes.py:186-209` |
| 3 | test | `the AR-385 suite's own case, updated: the same unreadable text below the cap now names its cause instead of returning a bare None` | 2026-09-04 | `tests/test_reply_budget_truncation.py:404-417` |
| 3 | command-output | `the turn 206 shape reports provider_model_text_not_json with reply_truncated False, beside the deadline abort on the same transport` | 2026-09-04 | `docs/roadmap/acceptance/evidence/AR-392-evidence-20260904.txt:20-21` |
| 4 | file | `call_attempted carries whether a request left; failure_reason keeps its ADR-0204 meaning and the move is stated where the field is defined` | 2026-09-04 | `agency_runtime/core/structured_provider.py:128-142` |
| 4 | file | `the staffing loop sets called and keeps the spend for an attempted failure, releases the budget for a refusal` | 2026-09-04 | `agency_runtime/core/workforce/inference.py:1721-1745` |
| 4 | file | `the hiring loop records a refusal as skipped, which is already its word for a call it did not make, and releases the budget` | 2026-09-04 | `agency_runtime/core/workforce/hiring.py:848-866` |
| 4 | file | `_CallBudget.release on the hiring budget, mirroring the staffing one` | 2026-09-04 | `agency_runtime/core/workforce/hiring.py:656-660` |
| 4 | test | `test_a_failure_after_the_request_spends_its_call_and_a_refusal_does_not asserts budget.used 1 and 0 for the two shapes` | 2026-09-04 | `tests/test_transport_failure_causes.py:301-343` |
| 4 | test | `test_the_hiring_loop_marks_a_refusal_skipped_and_a_failure_failed` | 2026-09-04 | `tests/test_transport_failure_causes.py:346-372` |
| 4 | test | `test_the_two_halves_of_the_vocabulary_do_not_overlap and test_a_refusal_before_any_request_says_no_call_was_made` | 2026-09-04 | `tests/test_transport_failure_causes.py:215-234` |
| 4 | test | `test_the_compatibility_wrapper_still_returns_none_for_a_named_failure pins that a caller which only asked "is None?" is not handed a named failure as a successful empty answer` | 2026-09-04 | `tests/test_transport_failure_causes.py:237-250` |
| 5 | file | `_workforce_timeout_checks states the effective seconds per routed profile, names the deployment timeout the runtime cannot read, and names the code an aborted call is recorded under` | 2026-09-04 | `agency_runtime/core/doctor.py:839-878` |
| 5 | file | `run_doctor includes the timeout report after the credential checks` | 2026-09-04 | `agency_runtime/core/doctor.py:1018-1018` |
| 5 | test | `test_doctor_states_the_effective_timeout_of_each_routed_profile asserts one pass check naming every routed profile` | 2026-09-04 | `tests/test_transport_failure_causes.py:379-405` |
| 5 | command-output | `installed configuration, read-only: six routed profiles at 30s (agency-default, agency-planner, agency-recruiter, agency-recruiter-critic, agency-hiring, agency-security) and four at 120s -- the static half of the AR-392 observation, confirmed live` | 2026-09-04 | `docs/roadmap/acceptance/evidence/AR-392-evidence-20260904.txt:26-27` |

## Verification

| Criterion | Verdict | Verifier run | Evidence digest | Observed | Reason |
|---|---|---|---|---|---|
| 1 | satisfied | `AR-392.1-20260904-48397c06` | `cd7a746a879db7f54f8d2e5a8ef01f574247cce392492fe202ce800f661edd15` | 2026-09-04 | inference.py:1722-1794 and hiring.py:845-896 split a bare None on the same latency >= timeout test into the same distinct code provider_call_timed_out (reply_budget.py:84,112); both attempts carry latency_ms and timeout_ms, and test_transport_failure_causes.py:257-305 asserts all three match. |
| 2 | satisfied | `AR-392.2-20260904-02ddd5a0` | `9a95539c172dbb0e1c69f6c9f84887dd0f674c9c46956cf46ca8b779d498d965` | 2026-09-04 | structured_provider.py:781-783 routes the still-blanket except through _transport_exception_cause (:634-653), mapping HTTPError to provider_http_status_error with exc.code; http_status rides on the result (:142) and receipt (:175), and tests/test_transport_failure_causes.py:117-141 pins 401/429/502. |
| 3 | satisfied | `AR-392.3-20260904-d275c93b` | `439aefad3cca0b5bb4fa11033bb2b148e1d4d592133a859b0dfacbe3fe1f097c` | 2026-09-04 | structured_provider.py:799-808 returns PROVIDER_MODEL_TEXT_NOT_JSON only when not truncated; reply_budget.py:72,84,92 keep it distinct from truncation and timeout; test_transport_failure_causes.py:181-205 reproduces the capture391 turn 206 shape and pins that distinction with reply_truncated False. |
| 4 | satisfied | `AR-392.4-20260904-6b11cb4b` | `6448181c7db410a833776668b9c262977b2a3b06aae5b0115a2e760ec4b0fade` | 2026-09-04 | inference.py:1731-1740 sets called and keeps the spend when call_attempted else releases; hiring.py:854-868 releases and marks skipped for a refusal; structured_provider.py:131-142 documents the split; snapshot tests at lines 441 and 484 assert used==1 vs 0, and 224-227 keeps the ADR-0204 meaning. |
| 5 | satisfied | `AR-392.5-20260904-dbfa6c2f` | `d710d9af6f8fa9a3bb32cc0e7fdebbed9a2f6c178a5a9c1a9092b1bea342996a` | 2026-09-04 | doctor.py:839-881 emits workforce_profile_timeouts stating each routed profile's effective seconds, wired at doctor.py:1018 into run_doctor used by the CLI; tests/test_transport_failure_causes.py:520-546 asserts every profile name, and two evidence files record the live 10-profile output. |

## Builder notes

New tests 14, all passing. The eleven bare `return None` statements the issue
counted inside `invoke_structured_provider_result` are zero on the branch and
eleven on `main`, measured by AST rather than by grep.

Four existing expectations pinned the code this issue removes and were updated
to the new contract, each with the reason stated at the assertion:
`test_invalid_primary_content_advances_to_the_content_fallback_provider` and
`test_a_no_response_attempt_still_carries_the_stamped_budget` (both now
`provider_call_failed`, the invoker returning at once), the AR-385 case for
unreadable model text (now `provider_model_text_not_json`), and the AR-388
case for a refused connection (now `provider_call_failed`, the residual code,
correctly distinct from the credential refusal that never reaches a socket).

## Not established here

The 30-versus-45-second ordering is not fixed by this change. It is operator
configuration, the runtime cannot read the deployment's figure, and what is
delivered is the report against which an operator makes the comparison.

No receipt written by a live staffing turn is included: the transport cases are
driven through the test seam, and the doctor report reads the installed
configuration without calling the gateway. A live turn carrying one of the new
codes onto a durable receipt is the remaining evidence, and it needs a shell
with the credential sourced.
