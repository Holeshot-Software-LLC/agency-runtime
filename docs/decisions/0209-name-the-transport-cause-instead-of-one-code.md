---
title: "Name the transport cause instead of one code"
status: accepted
category: decisions
created: 2026-09-04
updated: 2026-09-04
tags: [workforce, inference, transport, timeouts, receipts, doctor, observability]
related:
  - docs/roadmap/issue-AR-392-transport-failures-collapse-to-one-code.md
  - docs/roadmap/issue-AR-378-hiring-failure-records-no-attempt.md
  - docs/roadmap/issue-AR-388-unset-credential-reads-as-provider-unavailable.md
  - docs/roadmap/issue-AR-385-structured-reply-budget-truncates-nominations-silently.md
  - docs/roadmap/issue-AR-304-preserve-recruiter-critic-validation-diagnostics.md
  - docs/roadmap/handoffs/issue-AR-383.md
  - docs/decisions/0199-give-each-inference-stage-its-own-reply-budget.md
  - docs/decisions/0204-name-the-credential-the-launching-environment-never-carried.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
id: ADR-0209
type: decision
deciders: [owner]
---

# ADR-0209: Name the transport cause instead of one code

## Status

**Accepted 2026-09-04.** Item 2 of the AR-383 capsule's next package, filed
as AR-392.

## Context

`invoke_structured_provider_result` returned a bare `None` from eleven places
for causes with nothing in common: a prompt, schema, body or timeout outside
its bound; a provider unsafe to call as configured; an allowlisted CLI adapter
that produced no object; the runtime's own deadline aborting a call in flight;
a non-2xx status the gateway returned; a body that was not JSON; and model
text inside a complete body that was not a JSON object. One branch of
`_invoke_stage` stamped `provider_no_valid_response` over all of them.

Two of those causes were separated by hand on 2026-09-04, during the AR-391
and AR-383 captures, having previously been read as one shape. Every workforce
profile carries `timeout_ms: 30000` while every deployment behind
`task-agency-planner-v2`, `task-agency-recruiter-v2` and
`task-agency-critic-v2` carries `timeout: 45.0`, so a call the gateway would
have answered between 30 and 45 seconds is aborted by the runtime's own socket
deadline and no body ever arrives; observed at exactly 30.04 s. Separately,
one deployment emits a misplaced brace: HTTP 200, 5330 characters, failing at
character 257 because a candidate object closes before its `score`, with the
body ending complete. Nothing on the receipt told these apart, and recovering
the distinction took a capture harness.

The runtime already knew how to do better in two neighbouring cases, both
built for this reason. ADR-0199 gives a reply cut at the completion cap its own
code by returning evidence instead of `None`. ADR-0204 gives a credential the
environment never carried its own code through `failure_reason`. Everything
between those two named answers was one undifferentiated code. This is the
AR-388 and AR-304 shape in a fourth place: the runtime holds the fact that
explains the failure and throws it away before anything durable records it.

The hiring stage loop already drew a distinction the staffing stage loop could
not, over the same transport: it timed the call itself and split a bare `None`
from the outside into `provider_call_timed_out` and `provider_call_failed`.
One loop could tell an operator what happened and the other could not.

## Decision

1. **Close the divergence between the two stage loops first.** `_invoke_stage`
   times its call the way the hiring loop always has and applies the same
   outside-in split: a bare `None` whose elapsed time reached the profile's
   timeout is `provider_call_timed_out`, anything else is
   `provider_call_failed`, and both carry `latency_ms`. This is sound because
   the deadline handed to the transport is never raised above
   `provider.timeout`, so reaching it is a fact and not a guess. Both loops now
   read the two codes from `reply_budget`, so an identical failure cannot be
   classified one way in one loop and another way in the other.

2. **The transport names why it gave up, from a closed vocabulary**, returning
   a result with an empty value rather than a bare `None`:
   `provider_call_timed_out` for the runtime's own deadline,
   `provider_http_status_error` with the status kept on the result,
   `provider_response_not_json`, `provider_model_text_not_json` for a complete
   body whose model text is not an object, and `provider_call_failed` as the
   residual. Before any request leaves: `provider_request_invalid`,
   `provider_unsafe_configuration`, `provider_cli_no_object`, beside ADR-0204's
   `provider_credential_env_unset`.

3. **`failure_reason` keeps one meaning; `call_attempted` carries the other.**
   The reason said "no call was made at all", and the stage loop acted on that
   meaning by releasing the call budget and not setting `called`. Widening the
   vocabulary past refusals breaks that reading, so the fact moved deliberately
   to its own field rather than by accident. A failure after the request left
   spends its call and counts as `called`; a refusal before still gives the
   budget back and does not. The hiring loop records the latter as `skipped`,
   which is already its word for a call it did not make.

4. **The blanket `except` stays blanket.** Nothing here lets an unexpected
   exception escape the transport. Only the classification of what is already
   caught changes, and anything unrecognised stays on the residual code rather
   than being folded into a named one. `open_no_redirect` re-raises the
   status-bearing `HTTPError` deliberately; discarding it is what made a 429,
   a 401 and a 502 one code with no status recorded anywhere.

5. **A caller asks `carries_no_answer`, not `is None`.** A named failure is a
   result with an empty value, so a caller that only tested for `None` would
   read it as a successful empty answer. The compatibility wrapper and the
   upstream-selection eval ask the new question.

6. **The ordering of the two deadlines is operator configuration, and the
   runtime reports its half.** `timeout_ms` and the deployment timeout must be
   set so the runtime's deadline is the outer one, and the runtime cannot see
   the deployment's value to check it. `agency doctor` now states the effective
   seconds of each routed workforce profile, so the comparison an operator had
   to make by hand is made against a printed number.

## Consequences

An operator reading a receipt can now tell a deadline the runtime imposed on
itself from a reply the deployment malformed, without a capture harness. The
receipt's `provider_attempts` carry the cause and, for a non-2xx answer, the
status.

`provider_no_valid_response` is no longer written by the staffing stage loop.
Three tests that pinned it, and one that pinned a bare `None` for unreadable
model text, were updated to the new contract; a fourth, in the AR-388 suite,
now reads `provider_call_failed` for a refused connection, which is the
residual code and correctly distinct from both the deadline abort and the
credential refusal that never reaches a socket.

The 30-versus-45-second ordering itself is not fixed here. It is operator
configuration either way, and `agency doctor` printing the effective figure is
what the runtime owes; on the installed configuration it reports six routed
profiles at 30 s and four at 120 s, which is the static half of the AR-392
observation confirmed live.

Nothing here selects, ranks or filters a specialist. The change is in what the
runtime says about why a call it made did not come back.
