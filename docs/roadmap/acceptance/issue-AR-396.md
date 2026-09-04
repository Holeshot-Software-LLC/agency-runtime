---
title: "AR-396 acceptance verification record"
status: active
category: roadmap
created: 2026-09-04
updated: 2026-09-04
tags: [acceptance, verification]
related:
  - docs/roadmap/issue-AR-396-a-non-json-reply-gets-no-second-ask.md
  - docs/decisions/0212-ask-again-when-a-complete-reply-is-not-json.md
supersedes: []
superseded_by: null
type: acceptance-verification
issue_id: AR-396
candidate_commit: 551d08db7faf3f5f3b8e85aebc6e0d0b74231811
evidence_cutoff: 2026-09-04
tracker_url: null
---

# AR-396 acceptance verification record

`provider_model_text_not_json` now gets one bounded second ask on the same
provider, naming the fault the way the truncation retry names a cut, while
every other cause after the request still ends the provider on one call. The
first attempt is recorded exactly as it is today.

Every criterion is evidenced from the source and from a suite that drives the
stage loop through the invoker seam. The live figures in the evidence file are
the measurement that motivated the change, not a gate: no live gateway call is
required to verify any criterion below.

## Builder evidence

| Criterion | Kind | Artifact | Observed | Source |
|---|---|---|---|---|
| 1 | file | `the transport-failure branch retries only when the reason is PROVIDER_MODEL_TEXT_NOT_JSON and a semantic attempt remains, on the same provider, with the same budget and the same attempt bound` | 2026-09-04 | `agency_runtime/core/workforce/inference.py:1743-1767` |
| 1 | file | `max_semantic_attempts is the same allowance the truncation and contract-invalid branches use, and budget.consume gates every attempt` | 2026-09-04 | `agency_runtime/core/workforce/inference.py:1691-1709` |
| 1 | test | `test_a_non_json_reply_is_asked_again_and_the_second_reply_is_applied asserts the parsed second reply, two attempts, and budget.used 2` | 2026-09-04 | `tests/test_non_json_reply_second_ask.py:120-131` |
| 2 | file | `the retry appends a [RUNTIME VALIDATION FEEDBACK] block naming prior_response_status not_json and the required action, in the shape the truncation retry uses at :1801-1811` | 2026-09-04 | `agency_runtime/core/workforce/inference.py:1754-1766` |
| 2 | test | `test_the_second_ask_names_the_fault_and_keeps_the_stage_system_prompt asserts the feedback block is absent from the first prompt, present in the second, that the second extends the first, and that the stage's own system prompt is kept` | 2026-09-04 | `tests/test_non_json_reply_second_ask.py:134-150` |
| 3 | file | `the retry condition names one code; every other member of TRANSPORT_FAILURE_AFTER_REQUEST falls through to break` | 2026-09-04 | `agency_runtime/core/workforce/inference.py:1750-1767` |
| 3 | file | `the membership of the two halves of the transport split, unchanged` | 2026-09-04 | `agency_runtime/core/reply_budget.py:82-130` |
| 3 | test | `test_every_other_cause_after_the_request_still_ends_the_provider is parametrised over TRANSPORT_FAILURE_AFTER_REQUEST minus this one code and asserts one attempt, one call, and no parsed value for each` | 2026-09-04 | `tests/test_non_json_reply_second_ask.py:151-162` |
| 3 | test | `test_the_codes_this_split_is_written_against_are_the_ones_that_exist pins the set membership directly, so a cause added later cannot inherit either behaviour silently` | 2026-09-04 | `tests/test_non_json_reply_second_ask.py:190-199` |
| 4 | file | `the failed attempt is appended before the retry decision, with the transport's own reason_code, status failed and its latency` | 2026-09-04 | `agency_runtime/core/workforce/inference.py:1734-1742` |
| 4 | test | `test_a_non_json_reply_is_asked_again_and_the_second_reply_is_applied asserts the first attempt is still (provider_model_text_not_json, failed) and the second is (structured_response_applied, applied)` | 2026-09-04 | `tests/test_non_json_reply_second_ask.py:126-131` |
| 4 | test | `test_the_retry_is_bounded_by_the_semantic_attempt_allowance asserts two recorded attempts and workforce_inference_failed when both replies are non-JSON` | 2026-09-04 | `tests/test_non_json_reply_second_ask.py:165-176` |
| 4 | test | `test_the_retry_never_outruns_the_call_budget asserts a budget of one yields one attempt and workforce_call_budget_exhausted` | 2026-09-04 | `tests/test_non_json_reply_second_ask.py:179-187` |
| 5 | test | `the scripted invoker answers non-JSON once and valid JSON on the second ask; the stage applies the second reply and records both attempts` | 2026-09-04 | `tests/test_non_json_reply_second_ask.py:88-131` |
| 5 | command-output | `9 new tests pass at the candidate; the same 9 run against unfixed main give 4 failed, 5 passed, so the suite pins the change` | 2026-09-04 | `docs/roadmap/acceptance/evidence/AR-396-evidence-20260904.txt:30-34` |
| 5 | command-output | `the two live receipts that ended on one planner attempt, and the same payload answering with valid JSON ten times out of ten` | 2026-09-04 | `docs/roadmap/acceptance/evidence/AR-396-evidence-20260904.txt:4-27` |

## Verification

| Criterion | Verdict | Verifier run | Evidence digest | Observed | Reason |
|---|---|---|---|---|---|
| 1 | satisfied | `AR-396.1-20260904-1a2fa784` | `58149aa9a6637c728906c1a9bc21f84df757b1240ccaae14f8d9dfbf111d9ea2` | 2026-09-04 | inference.py:1750-1766 retries PROVIDER_MODEL_TEXT_NOT_JSON inside the same per-provider loop under the same semantic_attempt+1 < max_semantic_attempts guard the truncation branch uses at 1803, with budget.consume() at 1709 gating attempts; tests/test_non_json_reply_second_ask.py:120-187 pin it. |
| 2 | satisfied | `AR-396.2-20260904-aa63ddeb` | `ce6170764caa36d83323d3352ccfa55c80c9c5f030ffb8c13eced17900e2ef60` | 2026-09-04 | inference.py:1754-1766 builds the retry in the same [RUNTIME VALIDATION FEEDBACK] + _json_prompt shape as the truncation branch at :1805-1810, keying prior_response_status "not_json" and saying the prior reply was complete and not JSON; test_non_json_reply_second_ask.py:134-147 pins it. |
| 3 | satisfied | `AR-396.3-20260904-8dd0df1f` | `fc2ff942c98a25378ec349e6f36646d407c5947d95e59ce6efa7502853047c99` | 2026-09-04 | In the snapshot, inference.py:1750-1767 gates the retry solely on PROVIDER_MODEL_TEXT_NOT_JSON and breaks otherwise (returning workforce_inference_failed at 1856-1860); reply_budget.py:112-120 fixes the set, and tests 150-162 and 190-199 assert one attempt, one call, no parse for each other code. |
| 4 | satisfied | `AR-396.4-20260904-cda858d7` | `ee6432fa10b53aec9b5372371adc2a09e1013293c0b63804d45a14d73b54d6b1` | 2026-09-04 | inference.py:1733-1742 appends the attempt with status "failed" and reason_code=result.failure_reason before the retry branch at 1750, _attempt (1462-1492) stores both verbatim, and test_non_json_reply_second_ask.py:128-131 pins the first attempt as (PROVIDER_MODEL_TEXT_NOT_JSON, "failed"). |
| 5 | satisfied | `AR-396.5-20260904-3cc12433` | `247c981368c78ea416ffeaca3e5de60d71b0d7a67e9be50714e2093ab9758cf3` | 2026-09-04 | tests/test_non_json_reply_second_ask.py:120-131 scripts a non-JSON reply then valid JSON, asserting parsed equals the second reply and attempts records both (failed then applied); inference.py:1750-1767 holds the matching retry branch, and the evidence file reports 9 passed. |

## Builder notes

New tests 9. Four of them fail against `main` and five pass, which is the
intended split: the five that pass are the ones asserting behaviour this
change does not touch.

`structured_provider` is unchanged. The classification of the cause was
already correct after ADR-0209; what changed is only what `_invoke_stage` does
with it.

The seven failures in the wider preflight and dashboard surface
(`test_configuration_identity`, `test_dashboard`, `test_dashboard_operational`,
`test_http_server`, `test_http_server_coverage_complete`) are identical on
clean `main` — a `kernel v2` assertion against the v5 kernel — and are
untouched by this change.
