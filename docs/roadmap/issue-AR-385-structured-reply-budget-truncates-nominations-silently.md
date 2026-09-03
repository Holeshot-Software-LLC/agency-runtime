---
title: "AR-385: A fixed 2048-token reply budget truncates recruiter nominations, and the truncation is rejected as a contract failure with no record"
status: in_progress
category: roadmap
created: 2026-09-03
updated: 2026-09-03
tags: [workforce, recruiter, inference, provider, receipts]
related:
  - docs/decisions/0199-give-each-inference-stage-its-own-reply-budget.md
  - docs/roadmap/reference-workforce-inference-stages.md
  - docs/roadmap/issue-AR-373-recruiter-evidence-vocabulary.md
  - docs/roadmap/issue-AR-384-staff-decisions-die-on-uncoverable-typed-requirements.md
  - docs/roadmap/issue-AR-304-preserve-recruiter-critic-validation-diagnostics.md
  - docs/roadmap/issue-AR-383-inferred-subject-context-fails-its-own-projection.md
supersedes: []
superseded_by: null
type: issue
epic: reliability
issue_id: AR-385
priority: p1
tracker_url: null
depends_on: []
blocks: []
---

# AR-385: A fixed 2048-token reply budget truncates recruiter nominations, and the truncation is rejected as a contract failure with no record

## Problem

`_http_payload` (`core/structured_provider.py:344-411`) sends every
structured stage on every HTTP provider with `max_tokens: 2048` (line 405) or
`max_completion_tokens: 2048` (line 402). There is no configuration for it;
only the Ollama path uses a different figure (8192, line 370).

The recruiter route on this installation, `task-agency-recruiter-v2`, is
served first by `anthropic/MiniMax-M3` through the local LiteLLM gateway with
`thinking: adaptive` on the deployment, and Agency's `thinking_level: medium`
is sent as `reasoning_effort: medium`. The gateway maps that to a thinking
budget of 2048 tokens and caps the budget at `max_tokens - 1` because the
Anthropic-style API requires it (`litellm/llms/anthropic/chat/transformation.py`,
`_cap_thinking_budget_to_max_tokens`). Thinking and the visible answer share
the same 2048 tokens.

A recruiter nomination for a five- or six-unit plan does not fit. Captured
live 2026-09-03, three of nine MiniMax recruiter replies stopped at exactly
2048 completion tokens:

| turn | attempt | completion tokens | visible reply |
|---|---|---|---|
| token-bucket throttle, 6 units | first | 2048 | 4312 chars, last unit row has no `unit_id`, last rank has no `score` |
| login handler review, 4 units | repair | 2048 | third unit row has no `unit_id`, a rank carries an empty-string key |
| Node heap growth, 5 units | first | 2048 | fourth unit row has no `unit_id`, no `score` |

Each reply was syntactically closed JSON. The gateway's spend log for the
earlier forty-five-turn smoke shows the same cap on **5 of 55** MiniMax
recruiter calls, plus 2 replies under 60 tokens; the 5 gpt-5.5 calls it
records never hit it. A visible reply of about 1000 tokens leaving 2048 in
`completion_tokens` is the thinking share, which the gateway reports as
`reasoning_tokens: 0` for this deployment.

## Why it is invisible

1. `_NominationAccumulator.parse` (`core/workforce/inference.py:2866-2886`)
   raises a plain `ValueError("workforce nomination row is invalid")` when a
   row lacks one of its three keys. That is not a `_NominationValidationError`,
   so `_invoke_stage` records `provider_response_contract_invalid` with only a
   `validation_detail` string and no `validation_failures`.
2. The receipt projection keeps the failure list and the allowlisted reason
   codes and drops the detail (`core/preflight_failure.py:245-262`,
   `core/selector/receipt_projection.py:226`). The durable receipt therefore
   shows a rejected recruiter attempt with **nothing** attached. In the smoke,
   8 of 48 rejected recruiter attempts are blank this way (7 first attempts,
   1 repair). AR-304 filed this shape for the critic; this is the recruiter
   instance.
3. The repair prompt for this path (`inference.py:1403-1410`) tells the model
   its JSON "failed a deterministic semantic invariant: workforce nomination
   row is invalid" and asks it to re-evaluate identifiers and typed coverage.
   The model was cut off, not wrong. On both captured first-attempt
   truncations the retry, sent under the ordinary system prompt rather than
   the repair prompt, switched to prose evidence strings and died on
   `recruiter_candidate_positive_evidence_invalid` across every unit. The
   first attempt of the throttle turn had used clean hyphenated codes
   throughout; the feedback made the second worse.
4. When the cut-off JSON does not close, `_parse_model_text`
   (`structured_provider.py:239-257`) returns `None`, the attempt is recorded
   `provider_no_valid_response`, and with one configured provider entry the
   turn ends `inference_unavailable`. The smoke has 9 receipts whose only
   recruiter attempt is that code; at least one aligns with a 2048-token
   reply in the spend log (14:03:44 UTC). This issue does not claim the other
   eight.

## Current state

**Implemented on branch `claude/ar385-reply-budget` (2026-09-03)** per
[ADR-0199](../decisions/0199-give-each-inference-stage-its-own-reply-budget.md).
`core/reply_budget.py` names each stage's visible-reply budget (recruiter and
hiring stages 16384, planner 4096, critics 2048, subject 1024, reranker and
security review 4096); `_invoke_stage` and the hiring `_invoke` stamp it on
the provider entry they call with, and `reply_budget_tokens` on a profile or
provider entry overrides it (0 keeps the stage figure; 256 through 131072).
The transport adds the adapter's thinking allowance (1024/2048/4096/8192 for
a forwarded `low`/`medium`/`high`/`xhigh` on `litellm` and
`openai-compatible`) to the cap, reads the reply's usage and finish reason,
and flags a reply that reports `length` or spends exactly the cap. A flagged
reply that fails validation is recorded as `provider_response_truncated`
with a `truncation` object (`reply_budget_tokens`, `completion_cap_tokens`,
`completion_tokens`) on the routing and preflight-failure receipts, the
retry feedback carries `reply_truncation`, and a cut reply with no JSON
object comes back as the truncation rather than `None`. The accumulator
drops a unit row it cannot read: that unit surfaces as `missing_work_unit`
with the `recruiter_unit_row_shape_invalid` diagnosis and the repair asks for
exactly the lost units; a row for a unit outside the failed set is still
refused. `tests/test_reply_budget_truncation.py` (43 tests) pins the contract
and two curated decision-conformance mutations guard it.

Live re-measurement, five fresh wordings through `run_preflight` on the
branch runtime, recruiter served by the same MiniMax deployment
(`x-litellm-model-id b0b6f29c`), critic by `10729e08`, cap 18432 (evidence in
`docs/roadmap/acceptance/evidence/AR-385-evidence-20260903.txt`):

| turn | request | recruiter completion tokens | truncated | how the turn ended |
|---|---|---|---|---|
| 301 | token-bucket rate limiter, six units | **2277** first, 1620 repair | no | AR-373 evidence charset on every unit, then `staff_without_safe_team:domain` (AR-384 residue) |
| 302 | Node worker memory climb | 941 | no | structurally malformed JSON below the cap, `provider_no_valid_response`; not this issue |
| 303 | sign-in endpoint audit | none in 30.1 s | n/a | the recruiter profile's 30000 ms timeout, `provider_no_valid_response` |
| 304 | helix in my shell | 1433 | no | verifier accepted, strict critic vetoed (AR-386) |
| 305 | ripgrep, fd and bat | 1129 | no | verifier accepted, strict critic vetoed (AR-386) |

Turn 301 is the throttle criterion: a six-unit nomination completed at 2277
completion tokens, above the old 2048 cap, on the deployment that cut the
captured one. No live reply was cut under the new budgets. Two observations
belong to other work: turn 302's reply closed the `units` array early and
then continued, which is a structural model error the transport rightly
refuses and this issue does not claim; and turn 303 shows that once the cap
no longer bounds a long reply the profile's 30 s timeout does, which is the
operator's `timeout_ms` (see the AR-383 capsule constraints), not a branch
change.

The planner, critic, reranker, subject and hiring stages carry their own
figures now; none of them had hit the old cap in the captures.

## Approach

1. **Give the reply budget to the stage, not the transport.** A recruiter
   reply needs room for sixteen ranked rows per unit across up to sixteen
   units, plus whatever the deployment spends thinking. Make the budget a
   provider or stage setting, default it well above 2048 for the recruiter
   and hiring stages, and stop sharing it with the thinking allowance where
   the adapter lets the two be stated separately.
2. **Name truncation on the receipt.** The reply body carries `usage`; when
   `completion_tokens` equals the requested cap, record
   `provider_response_truncated` rather than a contract failure, and give the
   retry feedback that says so. A row missing a required key at the
   accumulator should also raise an allowlisted nomination failure
   (`missing_work_unit` fits a row that lost its `unit_id`) so the receipt
   and the repair prompt both carry the unit and the cause.
3. **Cost-tracking note.** The gateway logs `Cost tracking failed for
   model=gpt-5.5` on every gpt-5.5 reply and writes the spend row with zero
   tokens, so the spend log under-reports that deployment. Gateway
   configuration, recorded here so the numbers above are read correctly.

## Dependencies

- AR-373 owns the evidence-format rejection the misleading retry runs into.
- AR-384 owns the dominant failure that shares the same reason code.

## Acceptance

- [x] A recruiter reply that reaches the provider's completion cap is
      recorded on the receipt as truncated, with the stage and the cap, and
      the retry feedback names the cause.
- [x] The recruiter and hiring stages request a reply budget large enough
      that the captured six-unit throttle nomination completes on the
      deployment that served it.
- [x] No rejected recruiter attempt on a preflight receipt is blank: every
      one carries either `validation_failures` or a truncation record.
