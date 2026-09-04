---
title: "AR-396: A complete reply that is not JSON ends the stage on one call, while a cut one and a wrong one each get a second ask"
status: done
category: roadmap
created: 2026-09-04
updated: 2026-09-04
tags: [workforce, staffing, reliability, transport]
related:
  - docs/roadmap/issue-AR-392-transport-failures-collapse-to-one-code.md
  - docs/roadmap/issue-AR-385-structured-reply-budget-truncates-nominations-silently.md
  - docs/roadmap/issue-AR-394-recruiter-teams-fail-or-mis-select.md
  - docs/decisions/0209-name-the-transport-cause-instead-of-one-code.md
  - agency_runtime/core/workforce/inference.py
  - agency_runtime/core/structured_provider.py
  - agency_runtime/core/reply_budget.py
supersedes: []
superseded_by: null
type: issue
epic: reliability
issue_id: AR-396
priority: p1
tracker_url: null
depends_on: []
blocks: []
---

# AR-396: A complete reply that is not JSON ends the stage on one call, while a cut one and a wrong one each get a second ask

## Problem

`_invoke_stage` gives a stage two semantic attempts per provider
(`max_semantic_attempts = 2`, `inference.py:1691`). Which failures actually
get the second ask is decided by three adjacent branches, and they disagree
about one case:

- **The reply was cut** (`PROVIDER_RESPONSE_TRUNCATED`, `:1763-1787`): the
  attempt is recorded and the model is asked again, told it was interrupted
  rather than wrong.
- **The reply parsed but violated the contract**
  (`provider_response_contract_invalid`, `:1788-1820`): the attempt is
  recorded and the model is asked again through `_semantic_retry_prompts`.
- **The reply was complete and was not JSON**
  (`provider_model_text_not_json`): the attempt is recorded and the stage
  `break`s (`:1731-1762`). No second ask.

The third case is classified as a transport give-up because
`structured_provider` returns it through `_failed()` like a timeout or an HTTP
error. It is not one. Its own definition says so — `reply_budget.py:90-92`
calls it *"the sibling of `PROVIDER_RESPONSE_TRUNCATED`: nothing was cut, the
reply is simply not what the schema asked for"*, and
`structured_provider.py:800-804` reaches it only after a 200 whose body parsed
as a JSON object. A complete answer arrived; only its content was wrong. That
is the same class as the two branches above, and it is handled as the opposite
class.

The consequence is not one lost retry. Every workforce route in `agency.yaml`
resolves to exactly one provider profile, so `break` leaves no second provider
to fall to: the stage ends after a single call, with the call budget
untouched and a retry still allowed.

## Current state

**Measured 2026-09-04, `main` at `8a4ea67d`.**

Two of this session's own staffing turns ended exactly here, each on one
planner attempt and nothing else:

| receipt | reason code | attempts |
|---|---|---|
| 17:32:40Z | `workforce_inference_failed`, `["inference_invalid"]` | subject applied, then `planner:provider_model_text_not_json` |
| 17:44:25Z | `workforce_provider_unavailable`, `["inference_unavailable"]` | `planner:provider_model_text_not_json` |

The same planner payload the runtime builds, replayed 10 times against the
live gateway with the response cache bypassed, returned a parseable JSON
object **10 times out of 10**, in 12.87 s to 22.83 s, from the same deployment
`c2692490-cc91-5363-95f5-954745830cbb`. The reply that ended those two turns
was an outlier, and one more ask is very likely to have recovered the turn.

A second observation, recorded but not diagnosed here: the two receipts above
carry different `reason_code` values for the same terminal attempt code.
`_invoke_stage` returns `workforce_inference_failed` whenever a call was
attempted, and `provider_model_text_not_json` is in
`TRANSPORT_FAILURE_AFTER_REQUEST`, so the 17:44:25 receipt reading
`workforce_provider_unavailable` does not follow from that path alone.

## Why it matters

This is a staffing turn thrown away for a fault the runtime already knows how
to ask about, on a gateway that answers correctly ten times in a row. It is
also the cheapest of the current staffing failures to remove.

## Acceptance

- [x] `provider_model_text_not_json` gets one bounded second ask, on the same
      provider, under the same `max_semantic_attempts` and the same call
      budget as the truncation retry.
- [x] The retry names the fault to the model the way the truncation retry
      names the cut: the prior reply was complete and was not a JSON object.
- [x] Every other member of `TRANSPORT_FAILURE_AFTER_REQUEST` -- a timeout, an
      HTTP status error, a body that was not JSON, the residual -- still ends
      the provider without a semantic retry.
- [x] The first attempt is still recorded with `provider_model_text_not_json`
      and `status: failed`, so the evidence a receipt carries today does not
      change.
- [x] A test drives a provider that answers with non-JSON text once and valid
      JSON on the second ask, and asserts the stage applies the second reply
      and records both attempts.

## Rejected alternatives

- **Retry every transport failure.** A timeout has already spent the deadline
  and an HTTP error is not the model's to fix; retrying them spends budget on
  faults a second ask cannot address.
- **Fold it back into the parser rejection path.** There is no parsed value to
  build `_semantic_retry_prompts` feedback from; the truncation branch, which
  also has no parsed value, is the right shape to follow.
