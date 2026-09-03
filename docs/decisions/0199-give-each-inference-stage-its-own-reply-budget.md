---
title: "Give each inference stage its own reply budget and name a cut reply on the receipt"
status: accepted
category: decisions
created: 2026-09-03
updated: 2026-09-03
tags: [inference, provider, recruiter, hiring, receipts, configuration]
related:
  - docs/roadmap/issue-AR-385-structured-reply-budget-truncates-nominations-silently.md
  - docs/roadmap/issue-AR-384-staff-decisions-die-on-uncoverable-typed-requirements.md
  - docs/roadmap/issue-AR-373-recruiter-evidence-vocabulary.md
  - docs/roadmap/issue-AR-304-preserve-recruiter-critic-validation-diagnostics.md
  - docs/roadmap/reference-workforce-inference-stages.md
  - docs/decisions/0153-adopt-per-stage-inference-profile-routes.md
  - docs/decisions/0192-route-content-invalid-completions-to-a-content-fallback-profile.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
id: ADR-0199
type: decision
deciders: [owner]
---

# ADR-0199: Give each inference stage its own reply budget and name a cut reply on the receipt

## Status

**Accepted 2026-09-03.** Implements AR-385 item 1 of the AR-383 capsule's
next package. The owner delegated the approach as filed in the issue: the
budget belongs to the stage, and a cut reply is recorded as what it is.

## Context

`_http_payload` sent every structured stage on every HTTP provider with
`max_tokens: 2048` (or `max_completion_tokens: 2048`), a transport constant
with no configuration. The recruiter route on this installation is served
first by a thinking-enabled deployment through the local gateway; Agency
forwards `thinking_level: medium` as `reasoning_effort: medium`, the gateway
maps that to a 2048-token thinking budget and caps it at `max_tokens - 1`,
so the thinking and the visible reply shared one figure. A recruiter
nomination for a five- or six-unit plan does not fit. On the 2026-09-03
install smoke four of nine first recruiter replies stopped at exactly 2048
completion tokens as closed JSON with a unit row missing its `unit_id`, and
the gateway reported `finish_reason: stop` for every one of them.

The runtime then made the cut invisible. The nomination accumulator raised a
plain `ValueError` for the malformed row, which is not a
`_NominationValidationError`, so the attempt reached the receipt as
`provider_response_contract_invalid` with no `validation_failures`; the
projection dropped the detail; and the retry was told its JSON had "failed a
deterministic semantic invariant" and to re-evaluate its identifiers, after
which it drifted to prose evidence and died on AR-373's charset. When the
cut JSON did not close, the transport returned `None` and the turn ended
`inference_unavailable`. Eight of forty-eight rejected recruiter attempts on
the earlier forty-five-turn smoke were blank this way.

## Decision

1. **The stage owns the reply budget.** `STAGE_REPLY_BUDGET_TOKENS` in
   `core/reply_budget.py` names the visible-reply allowance per stage:
   16384 for the recruiter, hiring, hiring-repair and safety-repair stages,
   4096 for the planner, reranker and security review, 2048 for the critics,
   1024 for the subject stage. `_invoke_stage` and the hiring `_invoke` stamp
   the figure on the provider entry they call with, so every invoker sees it
   without a signature change. An operator may state `reply_budget_tokens`
   on an inference profile or a legacy provider entry (0 keeps the stage
   figure; otherwise 256 through 131072, refused at load outside that
   range), and a stated figure always wins. Structured callers outside the
   workforce stages keep the historical transport figures exactly.
2. **The thinking allowance is added to the cap, not taken from the reply.**
   The cap actually sent is the reply budget plus the thinking allowance the
   adapter forwards: 1024/2048/4096/8192 for a forwarded `low`/`medium`/
   `high`/`xhigh` on the `litellm` and `openai-compatible` adapters,
   mirroring the gateway's own `reasoning_effort` mapping, and nothing on
   adapters that forward no thinking. The sum is bounded at 131072.
3. **A reply that reaches the cap is truncated, whatever the finish reason
   says.** The transport reads the reply's own usage and finish reason. A
   provider that reports `length` or `max_tokens` is believed; one that
   reports `stop` while spending exactly the cap is not, because that is
   what the captured replies did. The result carries the reply budget, the
   cap, the completion tokens, the finish reason and the flag. A cut reply
   that holds no complete JSON object is returned with an empty value and
   the flag rather than as `None`.
4. **The receipt names the cut.** A rejected attempt whose reply was cut is
   recorded as `provider_response_truncated` instead of
   `provider_response_contract_invalid`, and both the routing receipt and
   the preflight-failure receipt carry a `truncation` object with the
   transport's three counts, bounded and content-free. The hiring `_invoke`
   records the no-object case under the same code.
5. **The retry is told it was cut.** Every bounded semantic retry that
   follows a truncated reply carries `reply_truncation` in its feedback:
   the three counts and the instruction that the failure above may be an
   effect of the cut and that the reply must come back complete and
   compact. The budget is not raised on retry.
6. **A cut nomination costs only the units it lost.** The accumulator drops
   a unit row it cannot read instead of refusing the reply; that unit
   surfaces as `missing_work_unit` with the closed diagnosis
   `recruiter_unit_row_shape_invalid` when its identity was readable, and
   as plain `missing_work_unit` when the cut took the identity too. The
   rows before the cut are kept, and the repair asks for exactly the lost
   units. A repair that omits a listed unit leaves it missing the same way;
   a repair that answers for a unit outside the failed set still breaks the
   repair contract, exactly as before.

## Consequences

- On the same deployment that cut the captured six-unit throttle nomination
  at 2048 tokens, a fresh six-unit throttle wording completed at 2277
  completion tokens under an 18432-token cap with no truncation. The turn
  then failed on AR-373's evidence charset and an AR-384 domain residue,
  which this decision does not claim.
- Every provider attempt on the routing result now carries
  `reply_budget_tokens`, `completion_cap_tokens`, `completion_tokens` and
  `reply_truncated`; the two durable receipts carry the `truncation` object
  only when the flag is true, so an unchanged attempt projects exactly as
  before.
- The provider cache identity binds the stated `reply_budget_tokens`, so a
  configured change of budget is a different cache key; the stage default is
  code and is not part of the identity.
- The subject and planner stages, which never hit the old cap, now send
  3072 and 6144 under a forwarded `medium`; their measured replies stay far
  below both.
- Once the cap no longer bounds a long reply, the profile's `timeout_ms`
  does: one of the five re-measured turns lost its recruiter call at the
  configured 30 s with no reply. The timeout is operator configuration, so
  this decision records the new binding constraint and changes nothing
  there.
- A reply that reaches the cap and still validates is applied and keeps the
  flag on its attempt, which is honest and rare.
- Not done: raising the budget on retry, adding the thinking allowance on the
  direct `anthropic` adapter (the transport disables thinking there), and
  carrying the three counts on the hiring case's own attempt record. The
  hiring stages get the budget and the reason code only.

## Alternatives

- **A larger transport constant.** Rejected: the planner, critic, reranker,
  recruiter and hiring stages return replies that differ by more than an
  order of magnitude, and one figure is either wasteful or too small for
  someone. The stage is the unit that knows its reply.
- **A configuration key only, with no stage default.** Rejected: every
  installation would have to state a figure per profile before the
  recruiter could staff a six-unit plan, and the AR-235 profile shape
  deliberately keeps profiles small.
- **Detect truncation from the finish reason alone.** Rejected by the
  evidence: every captured cut reply said `stop`.
- **Keep refusing a reply with an unreadable row.** Rejected: it threw away
  every complete row before the cut, sent the model a misleading repair, and
  left the receipt blank. Dropping the unreadable row invents nothing; the
  lost unit is named and re-asked.
- **Separate thinking and reply figures in the request.** The Anthropic
  Messages API and the gateway both count thinking inside `max_tokens`, so
  the two cannot be stated separately on this transport; adding the
  allowance to the cap is the same outcome.
