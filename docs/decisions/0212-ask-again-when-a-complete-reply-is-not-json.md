---
title: "Ask again when a complete reply is not JSON"
status: accepted
category: decisions
created: 2026-09-04
updated: 2026-09-04
tags: [workforce, inference, transport, staffing, reliability]
related:
  - docs/roadmap/issue-AR-396-a-non-json-reply-gets-no-second-ask.md
  - docs/roadmap/issue-AR-392-transport-failures-collapse-to-one-code.md
  - docs/roadmap/issue-AR-394-recruiter-teams-fail-or-mis-select.md
  - docs/roadmap/issue-AR-385-structured-reply-budget-truncates-nominations-silently.md
  - docs/decisions/0209-name-the-transport-cause-instead-of-one-code.md
  - docs/decisions/0199-give-each-inference-stage-its-own-reply-budget.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
id: ADR-0212
type: decision
deciders: [owner]
---

# ADR-0212: Ask again when a complete reply is not JSON

## Status

**Accepted 2026-09-04.** Filed as AR-396 while diagnosing why live staffing
turns stayed unstaffed after the launch environment was corrected.

## Context

ADR-0209 gave every transport cause its own name. One of those names,
`provider_model_text_not_json`, described something the other four do not: the
gateway answered, the body parsed as a JSON object, the reply was complete,
and only the model text inside it was not the JSON object the schema asked
for. `reply_budget.py` says as much where the code is defined — *the sibling
of `PROVIDER_RESPONSE_TRUNCATED`: nothing was cut, the reply is simply not
what the schema asked for*.

`_invoke_stage` nonetheless handled it as a transport give-up, because
`structured_provider` returns it through the same failure result as a timeout
or an HTTP status error. The branch that reads `result.failure_reason`
recorded the attempt and broke out of the semantic loop, while its two
neighbours — a reply cut at the completion cap, and a reply that parsed and
violated the contract — each asked once more.

That asymmetry graded the worst reply most leniently. A reply that arrived and
was slightly wrong was repaired; a reply that arrived and was entirely the
wrong shape was not. And because every workforce route in `agency.yaml`
resolves to exactly one provider profile, breaking the provider loop ended the
stage: one call, with a semantic attempt and call budget both still
unspent.

Measured on 2026-09-04, two staffing turns on this machine ended exactly there
— receipts at 17:32:40Z and 17:44:25Z, each carrying a single
`planner:provider_model_text_not_json` attempt — while the same planner
payload replayed ten times against the same gateway with the response cache
bypassed returned a parseable object ten times out of ten, in 12.87 s to
22.83 s.

## Decision

`provider_model_text_not_json` gets one bounded second ask, and nothing else
does.

- The failed attempt is still recorded first, with its own code and
  `status: failed`, so the receipt says what happened before the retry.
- The retry reuses the stage's own system prompt and appends a
  `[RUNTIME VALIDATION FEEDBACK]` block naming the fault as
  `prior_response_status: not_json`, in the shape the truncation retry already
  uses. The reply was the wrong shape, not the wrong answer, so there is no
  repair prompt to switch to.
- The retry is bounded by the same `max_semantic_attempts` and consumes the
  same call budget as every other attempt. A second non-JSON reply ends the
  provider.
- Every other member of `TRANSPORT_FAILURE_AFTER_REQUEST` — a timeout, a
  non-2xx status, a body that was not JSON, and the residual — still ends the
  provider without a semantic retry.

## Consequences

A stage can now spend two calls where it previously spent one, in exactly the
case where the first call bought nothing. The ceiling does not move: the
attempt bound and the call budget were already the limits, and this cause was
simply not reaching them.

Receipts gain a shape they could not previously show — two attempts on one
provider whose first is `provider_model_text_not_json` — and lose nothing:
the first attempt is recorded identically to today.

The distinction now rests on a code being in the right half of the transport
split. `tests/test_non_json_reply_second_ask.py` pins the membership of
`TRANSPORT_FAILURE_AFTER_REQUEST` directly, so a cause added later cannot
inherit either behaviour by accident.

## Alternatives rejected

- **Retry every transport failure.** A timeout has already spent the
  deadline, and an HTTP status error is not the model's to correct. Retrying
  them spends the budget on faults a second ask cannot address.
- **Route it through `_semantic_retry_prompts`.** Those prompts are built from
  a parsed value and a validation error, and here there is neither. The
  truncation branch, which also has no parsed value, is the right shape.
- **Raise `max_semantic_attempts`.** The allowance was never the limit; the
  branch that never used it was.
