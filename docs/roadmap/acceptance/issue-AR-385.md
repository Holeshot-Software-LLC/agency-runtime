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
  - docs/decisions/0202-read-the-recruiter-reply-where-no-safety-property-lives.md
supersedes: []
superseded_by: null
type: acceptance-verification
issue_id: AR-385
candidate_commit: pending
evidence_cutoff: 2026-09-03
tracker_url: null
---

# AR-385 acceptance verification record

Pending draft, held back once. Each workforce stage stamps its own reply
budget on the provider it calls with, the transport adds the adapter's
thinking allowance to the cap and reads the reply's usage, a reply that
reaches the cap is recorded as `provider_response_truncated` with the
transport's counts on both receipts and the retry is told it was cut, and a
nomination reply cut mid-row loses only the units whose rows could not be
read. Criterion 2 is evidenced live on the deployment that cut the captured
throttle nomination; criterion 1 by tests and by a live turn whose recruiter
budget was forced down in process so that a cut would occur. Criterion 3 was
not frozen at `0f70496c` because the ADR-0201 live run showed two rejected
attempt classes still blank on the receipt, a reply that was not a units
object and a reply the verifier rejected; ADR-0202 records both, and the rows
below cite the recording code, its tests, and the live and offline evidence.

## Builder evidence

| Criterion | Kind | Artifact | Observed | Source |
|---|---|---|---|---|
| 1 | file | `_reply_truncated believes a length or max_tokens finish reason and treats a reply that spent exactly the requested cap as cut even when the provider reports stop` | 2026-09-03 | `agency_runtime/core/structured_provider.py:380-391` |
| 1 | file | `invoke_structured_provider_result reads usage and finish reason, flags the cut reply, and returns a cut reply that holds no JSON object as the truncation rather than None` | 2026-09-03 | `agency_runtime/core/structured_provider.py:634-671` |
| 1 | file | `_invoke_stage records a cut reply as provider_response_truncated on the stage's attempt with the transport's counts, and puts the truncation into the retry feedback` | 2026-09-03 | `agency_runtime/core/workforce/inference.py:1456-1571` |
| 1 | file | `_reply_truncation_feedback names the reply budget, the cap, the tokens spent and the cause for the retry` | 2026-09-03 | `agency_runtime/core/workforce/inference.py:1299-1317` |
| 1 | file | `project_preflight_provider_attempts carries the truncation object on the stage's entry of the durable preflight-failure receipt` | 2026-09-03 | `agency_runtime/core/preflight_failure.py:227-273` |
| 1 | test | `test_the_stage_records_a_cut_reply_as_truncated_and_names_the_cut_on_the_retry asserts the reason code, the stamped budget, the counts on the attempt and the cut named in the retry prompt` | 2026-09-03 | `tests/test_reply_budget_truncation.py:429-474` |
| 1 | test | `test_a_reply_that_spends_exactly_the_cap_is_truncated_even_when_the_gateway_says_stop drives the HTTP transport with the captured reply shape` | 2026-09-03 | `tests/test_reply_budget_truncation.py:350-366` |
| 1 | command-output | `live turn 309 with the recruiter budget forced to 256 in process: both rejected recruiter attempts on the durable preflight-failure receipt read provider_response_truncated with reply_budget_tokens, completion_cap_tokens and completion_tokens 256` | 2026-09-03 | `docs/roadmap/acceptance/evidence/AR-385-evidence-20260903.txt:37-49` |
| 2 | file | `STAGE_REPLY_BUDGET_TOKENS gives the recruiter, hiring, hiring-repair and safety-repair stages 16384 visible-reply tokens` | 2026-09-03 | `agency_runtime/core/reply_budget.py:37-56` |
| 2 | file | `provider_for_stage stamps the stage budget on a provider entry unless the operator stated one` | 2026-09-03 | `agency_runtime/core/reply_budget.py:83-93` |
| 2 | file | `completion_cap_tokens adds the forwarded thinking allowance to the reply budget so the two no longer share one cap` | 2026-09-03 | `agency_runtime/core/reply_budget.py:115-136` |
| 2 | file | `_invoke_stage stamps the stage budget on every provider it calls, so the recruiter asks for 16384` | 2026-09-03 | `agency_runtime/core/workforce/inference.py:1470-1480` |
| 2 | file | `the hiring _invoke stamps the stage budget on every provider it calls, so the hiring stages ask for 16384` | 2026-09-03 | `agency_runtime/core/workforce/hiring.py:819-822` |
| 2 | test | `test_the_recruiter_and_hiring_stages_own_a_budget_the_old_constant_never_gave` | 2026-09-03 | `tests/test_reply_budget_truncation.py:256-262` |
| 2 | test | `test_the_http_payload_carries_the_stage_cap_not_a_transport_constant asserts max_tokens 18432 for a stamped recruiter under medium thinking, and the same cap on the other token parameters` | 2026-09-03 | `tests/test_reply_budget_truncation.py:298-326` |
| 2 | command-output | `live turn 301, fresh six-unit token-bucket wording on the MiniMax deployment that cut the captured throttle nomination at 2048: the nomination completed at 2277 completion tokens under an 18432 cap with no truncation` | 2026-09-03 | `docs/roadmap/acceptance/evidence/AR-385-evidence-20260903.txt:15-29` |
| 3 | file | `_NominationAccumulator.parse drops a unit row it cannot read so the unit surfaces as missing_work_unit with the unit-row diagnosis, and records a reply that is not a units object as missing_work_unit with recruiter_response_shape_invalid for every planned unit instead of raising a bare error` | 2026-09-03 | `agency_runtime/core/workforce/inference.py:3117-3202` |
| 3 | file | `project_nomination_failures projects nomination failures and, through _staffing_verification_failures, the verifier's unit=code rows onto both receipts; _nomination_failure_row admits a bare verifier row from STAFFING_VERIFIER_REASON_CODES so the rows survive the re-projection every reader applies` | 2026-09-03 | `agency_runtime/core/selector/receipt_projection.py:270-389` |
| 3 | file | `project_preflight_provider_attempts carries validation_failures, validation_reason_codes and the truncation object on each rejected attempt` | 2026-09-03 | `agency_runtime/core/preflight_failure.py:227-273` |
| 3 | test | `test_the_preflight_failure_receipt_is_never_blank_on_a_cut_reply asserts the truncation record, the validation_failures and the diagnosis on one projected attempt` | 2026-09-03 | `tests/test_reply_budget_truncation.py:651-664` |
| 3 | test | `test_an_empty_object_reply_is_repaired_before_the_turn_dies drives plan_and_staff_workforce through an empty-object recruiter reply and asserts the rejected attempt carries the units and the response-shape diagnosis` | 2026-09-03 | `tests/test_recruiter_reply_residue.py:409-437` |
| 3 | test | `test_a_verifier_rejection_projects_onto_the_attempt_row and test_verifier_rows_survive_the_re_projection_every_reader_applies assert the verifier's rows on the projected attempt, on write and on read` | 2026-09-03 | `tests/test_recruiter_reply_residue.py:488-565` |
| 3 | command-output | `eleven live turns on the ADR-0202 runtime: the two non-blank rejected attempts (206's not-a-units-object reply, 304's rows without scores) carry validation_failures and the diagnosis; 202's two verifier-rejected attempts were captured blank before the re-projection fix` | 2026-09-03 | `docs/roadmap/acceptance/evidence/AR-373-AR-385-residue-evidence-20260903.txt:47-76` |
| 3 | command-output | `202's captured verifier detail, projected with the final code: written rows and read-back rows identical, so the attempt is no longer blank on either receipt` | 2026-09-03 | `docs/roadmap/acceptance/evidence/AR-373-AR-385-residue-evidence-20260903.txt:78-92` |

## Verification

| Criterion | Verdict | Verifier run | Evidence digest | Observed | Reason |
|---|---|---|---|---|---|
