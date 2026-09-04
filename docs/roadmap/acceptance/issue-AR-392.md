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
candidate_commit: 03e302a5280291d26c89412d786487d07f40204c
evidence_cutoff: 2026-09-04
tracker_url: null
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
| 1 | file | `the hiring loop's own outside-in split, unchanged, and its comment on why reaching the deadline is a fact` | 2026-09-04 | `agency_runtime/core/workforce/hiring.py:869-884` |
| 1 | test | `test_the_staffing_loop_splits_a_bare_none_the_way_the_hiring_loop_does drives both loops with one invoker and one clock and asserts the same code and the same latency` | 2026-09-04 | `tests/test_transport_failure_causes.py:243-283` |
| 1 | test | `test_a_call_that_returned_early_is_a_failed_call_not_a_deadline_abort pins the other side of the split` | 2026-09-04 | `tests/test_transport_failure_causes.py:286-298` |
| 1 | command-output | `30.04s against the profile's own 30s deadline: both loops report provider_call_timed_out, latency_ms 30040` | 2026-09-04 | `docs/roadmap/acceptance/evidence/AR-392-evidence-20260904.txt:16-17` |
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
