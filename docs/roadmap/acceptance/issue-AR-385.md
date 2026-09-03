---
title: "AR-385 acceptance verification record"
status: active
category: roadmap
created: 2026-09-03
updated: 2026-09-03
tags: [acceptance, verification]
related:
  - docs/roadmap/issue-AR-385-structured-reply-budget-truncates-nominations-silently.md
  - docs/decisions/0199-give-each-inference-stage-its-own-reply-budget.md
supersedes: []
superseded_by: null
type: acceptance-verification
issue_id: AR-385
candidate_commit: pending
evidence_cutoff: 2026-09-03
tracker_url: null
---

# AR-385 acceptance verification record

Pending draft. Each workforce stage stamps its own reply budget on the
provider it calls with, the transport adds the adapter's thinking allowance
to the cap and reads the reply's usage, a reply that reaches the cap is
recorded as `provider_response_truncated` with the transport's counts on both
receipts and the retry is told it was cut, and a nomination reply cut mid-row
loses only the units whose rows could not be read. Criterion 2 is evidenced
live on the deployment that cut the captured throttle nomination; criteria 1
and 3 are evidenced by tests and by a live turn whose recruiter budget was
forced down in process so that a cut would occur.

## Builder evidence

| Criterion | Kind | Artifact | Observed | Source |
|---|---|---|---|---|
| 1 | file | `_reply_truncated believes a length or max_tokens finish reason and treats a reply that spent exactly the requested cap as cut even when the provider reports stop` | 2026-09-03 | `agency_runtime/core/structured_provider.py:380-391` |
| 1 | file | `invoke_structured_provider_result reads usage and finish reason, flags the cut reply, and returns a cut reply that holds no JSON object as the truncation rather than None` | 2026-09-03 | `agency_runtime/core/structured_provider.py:634-671` |
| 1 | file | `_invoke_stage records a cut reply as provider_response_truncated on the stage's attempt with the transport's counts, and puts the truncation into the retry feedback` | 2026-09-03 | `agency_runtime/core/workforce/inference.py:1474-1544` |
| 1 | file | `_reply_truncation_feedback names the reply budget, the cap, the tokens spent and the cause for the retry` | 2026-09-03 | `agency_runtime/core/workforce/inference.py:1272-1290` |
| 1 | file | `project_preflight_provider_attempts carries the truncation object on the stage's entry of the durable preflight-failure receipt` | 2026-09-03 | `agency_runtime/core/preflight_failure.py:226-272` |
| 1 | test | `test_the_stage_records_a_cut_reply_as_truncated_and_names_the_cut_on_the_retry asserts the reason code, the stamped budget, the counts on the attempt and the cut named in the retry prompt` | 2026-09-03 | `tests/test_reply_budget_truncation.py:429-474` |
| 1 | test | `test_a_reply_that_spends_exactly_the_cap_is_truncated_even_when_the_gateway_says_stop drives the HTTP transport with the captured reply shape` | 2026-09-03 | `tests/test_reply_budget_truncation.py:350-366` |
| 1 | command-output | `live turn 309 with the recruiter budget forced to 256 in process: both rejected recruiter attempts on the durable preflight-failure receipt read provider_response_truncated with reply_budget_tokens, completion_cap_tokens and completion_tokens 256` | 2026-09-03 | `docs/roadmap/acceptance/evidence/AR-385-evidence-20260903.txt:37-49` |
| 2 | file | `STAGE_REPLY_BUDGET_TOKENS gives the recruiter, hiring, hiring-repair and safety-repair stages 16384 visible-reply tokens` | 2026-09-03 | `agency_runtime/core/reply_budget.py:37-56` |
| 2 | file | `provider_for_stage stamps the stage budget on a provider entry unless the operator stated one` | 2026-09-03 | `agency_runtime/core/reply_budget.py:83-93` |
| 2 | file | `completion_cap_tokens adds the forwarded thinking allowance to the reply budget so the two no longer share one cap` | 2026-09-03 | `agency_runtime/core/reply_budget.py:115-136` |
| 2 | file | `_invoke_stage stamps the stage budget on every provider it calls, so the recruiter asks for 16384` | 2026-09-03 | `agency_runtime/core/workforce/inference.py:1448-1451` |
| 2 | file | `the hiring _invoke stamps the stage budget on every provider it calls, so the hiring stages ask for 16384` | 2026-09-03 | `agency_runtime/core/workforce/hiring.py:819-822` |
| 2 | test | `test_the_recruiter_and_hiring_stages_own_a_budget_the_old_constant_never_gave` | 2026-09-03 | `tests/test_reply_budget_truncation.py:256-262` |
| 2 | test | `test_the_http_payload_carries_the_stage_cap_not_a_transport_constant asserts max_tokens 18432 for a stamped recruiter under medium thinking, and the same cap on the other token parameters` | 2026-09-03 | `tests/test_reply_budget_truncation.py:298-326` |
| 2 | command-output | `live turn 301, fresh six-unit token-bucket wording on the MiniMax deployment that cut the captured throttle nomination at 2048: the nomination completed at 2277 completion tokens under an 18432 cap with no truncation` | 2026-09-03 | `docs/roadmap/acceptance/evidence/AR-385-evidence-20260903.txt:15-29` |
| 3 | file | `_NominationAccumulator.parse drops a unit row it cannot read and lets that unit surface as missing_work_unit with the recruiter_unit_row_shape_invalid diagnosis instead of raising a bare ValueError that reached the receipt blank` | 2026-09-03 | `agency_runtime/core/workforce/inference.py:3023-3091` |
| 3 | file | `_row_unit_id reads the planned unit a row names, or none when the cut took the identity` | 2026-09-03 | `agency_runtime/core/workforce/inference.py:2979-2989` |
| 3 | file | `project_reply_truncation projects the bounded truncation record that both receipts carry` | 2026-09-03 | `agency_runtime/core/selector/receipt_projection.py:365-383` |
| 3 | file | `project_preflight_provider_attempts carries validation_failures, validation_reason_codes and the truncation object on each rejected attempt` | 2026-09-03 | `agency_runtime/core/preflight_failure.py:226-272` |
| 3 | test | `test_a_row_cut_mid_way_loses_only_its_own_unit_and_the_repair_completes_it asserts the missing_work_unit failure with the unit-row diagnosis and the repair completing the plan` | 2026-09-03 | `tests/test_reply_budget_truncation.py:561-575` |
| 3 | test | `test_the_preflight_failure_receipt_is_never_blank_on_a_cut_reply asserts the truncation record, the validation_failures and the diagnosis on one projected attempt` | 2026-09-03 | `tests/test_reply_budget_truncation.py:651-664` |
| 3 | test | `test_a_cut_first_nomination_is_repaired_from_the_units_it_lost drives plan_and_staff_workforce through a cut first reply and asserts the rejected attempt carries the diagnosis and the repair asks only for the lost unit` | 2026-09-03 | `tests/test_reply_budget_truncation.py:849-914` |
| 3 | command-output | `live turn 309: the first rejected recruiter attempt carries validation_failures naming the seven lost units and the truncation record; the repair attempt carries the truncation record; neither is blank` | 2026-09-03 | `docs/roadmap/acceptance/evidence/AR-385-evidence-20260903.txt:42-49` |

## Verification

| Criterion | Verdict | Verifier run | Evidence digest | Observed | Reason |
|---|---|---|---|---|---|
