---
title: "AR-392: Every transport failure reads as one code, so a runtime timeout and a malformed reply are indistinguishable"
status: open
category: roadmap
created: 2026-09-04
updated: 2026-09-04
tags: [workforce, inference, transport, timeouts, receipts, observability]
related:
  - docs/roadmap/issue-AR-388-unset-credential-reads-as-provider-unavailable.md
  - docs/roadmap/issue-AR-385-structured-reply-budget-truncates-nominations-silently.md
  - docs/roadmap/issue-AR-378-hiring-failure-records-no-attempt.md
  - docs/roadmap/issue-AR-304-preserve-recruiter-critic-validation-diagnostics.md
  - docs/roadmap/issue-AR-383-inferred-subject-context-fails-its-own-projection.md
  - docs/roadmap/handoffs/issue-AR-383.md
  - docs/decisions/0199-give-each-inference-stage-its-own-reply-budget.md
  - docs/decisions/0204-name-the-credential-the-launching-environment-never-carried.md
  - agency_runtime/core/structured_provider.py
  - agency_runtime/core/workforce/inference.py
  - agency_runtime/core/workforce/hiring.py
supersedes: []
superseded_by: null
type: issue
epic: reliability
issue_id: AR-392
priority: p1
tracker_url: null
depends_on: []
blocks: []
---

# AR-392: Every transport failure reads as one code, so a runtime timeout and a malformed reply are indistinguishable

## Problem

When a stage fails at the transport, the attempt on the receipt says
`provider_no_valid_response` and nothing else. That code is stamped by one
branch of `_invoke_stage`
(`agency_runtime/core/workforce/inference.py:1718`, code at `:1724`) whenever
the structured transport handed back a bare `None`, and
`invoke_structured_provider_result` returns a bare `None` from eleven distinct
places for causes with nothing in common:

- the request could never be built: a prompt or system prompt that is not a
  string, is empty, carries a NUL or exceeds its byte cap; a schema over its
  cap; a non-positive timeout; a serialised body over its cap
  (`structured_provider.py:602`, `:613`, `:615`, `:619`, `:664`);
- the provider is not safe to call as configured, so no call is made
  (`:655`);
- an allowlisted CLI adapter produced no object (`:630`);
- **the call was made and the runtime's own deadline aborted it** — either
  `_read_http_response` running past `deadline` and returning `None`
  (`:677`), or the socket raising into the blanket `except Exception` at
  `:675`;
- **the gateway answered a non-2xx status.** `open_no_redirect` treats an
  `HTTPError` deliberately: it closes the socket-backed body and re-raises
  the *status-bearing* exception. The same blanket `except Exception` at
  `:675` then discards it, so a 429 rate limit, a 401 on a rejected key and a
  502 from a dead deployment are one code with no status recorded anywhere;
- the response body was not a JSON object (`:681`);
- **the body was JSON, complete, and the model text inside it was not a JSON
  object** (`:692`, when `truncated` is false).

The transport already knows how to do better in two neighbouring cases, and
both were built for exactly this reason. ADR-0199 gives a reply cut by the
completion cap its own code, `provider_response_truncated`, by returning
evidence instead of `None` (`:692` is the branch that declines to). ADR-0204
gives a credential the launching environment never carried its own code,
`provider_credential_env_unset`, through
`StructuredProviderResult.failure_reason` (`:122`, `:535`). Everything
between those two named answers is a single undifferentiated code.

This is the AR-388 and AR-304 shape in a fourth place: the runtime holds the
fact that explains the failure and throws it away before anything durable can
record it.

## Current state

Two causes were separated by hand on 2026-09-04 during the AR-391 and AR-383
captures, having previously been read as one shape. Both are recorded in
`docs/roadmap/handoffs/issue-AR-383.md`:

1. **The runtime's timeout is below the gateway's.** Every workforce profile
   in `agency.yaml` carries `timeout_ms: 30000`; every deployment behind
   `task-agency-planner-v2`, `task-agency-recruiter-v2` and
   `task-agency-critic-v2` carries `timeout: 45.0`. A call the gateway would
   have answered between 30 and 45 seconds is aborted by the runtime's own
   socket deadline, so no body ever arrives. Observed at exactly 30.04 s on
   capture391 turn 201 and on capture392 turn 205 (twice).
2. **One deployment emits a misplaced brace.** capture391 turn 206: HTTP 200,
   5330 characters from `b0b6f29c` (MiniMax-M3, order 1 behind the recruiter
   alias), failing at character 257 because a candidate object closes before
   its `score`. The body ends complete, so this is not a completion-cap cut
   and `provider_response_truncated` does not apply.

The installed configuration confirms the first half statically: of the ten
profiles in `~/.agency-runtime/agency.yaml`, six carry `timeout_ms: 30000`
(`agency-default`, `agency-planner`, `agency-recruiter`,
`agency-recruiter-critic`, `agency-hiring`, `agency-security`), while
`agency-hiring-critic`, the router and both local Ollama profiles carry
`120000`. The transport's own ceiling,
`MAX_STRUCTURED_TIMEOUT_SECONDS`, is 120.0, so 30 s is a configured choice
and not a clamp.

Nothing on the receipt separates these. Both arrive as one
`provider_no_valid_response` attempt, and the stage outcome is
`workforce_inference_failed` in both cases, because `called` is set at
`inference.py:1717` before the `result is None` branch is reached.

## The same transport, classified twice

The hiring stage loop already draws the distinction the staffing stage loop
cannot, over the same transport and without any change to it
(`agency_runtime/core/workforce/hiring.py:833`, `:841`, `:854`). It times the
call itself, and on a bare `None` it splits the outcome from the outside:
`provider_call_timed_out` when the elapsed time reached the profile's
timeout, `provider_call_failed` otherwise, with `latency_ms` on the failed
attempt either way. Its own comment says why that is sound -- the deadline
handed to the transport is never raised above `provider.timeout`, so reaching
it is a fact and not a guess.

`_invoke_stage` does none of this. It does not time the call, so it cannot
even make the inference hiring makes, and its bare-`None` branch has no
latency to record. Two stage loops over one transport report the same failure
at different resolutions, and the coarser one is the one that staffs every
turn.

AR-378 recorded the residual limit in the tree as well, at `hiring.py:707`:
the provider seam returns a bare `None`, so those are the only failure classes
hiring can witness for itself, and distinguishing a transport error from a
schema rejection would need `invoke_structured_provider_result` to surface why
it gave up. That is this issue, asked for from the other side and standing
since AR-378.

## Approach

Implemented under ADR-0209.

1. **Close the divergence first; it costs nothing.** Give `_invoke_stage` the
   timing the hiring loop already has (`hiring.py:833`, `:841`) and the same
   outside-in split: a bare `None` whose elapsed time reached the profile's
   timeout is `provider_call_timed_out`, anything else is a failed call, and
   both carry `latency_ms`. This needs no transport change, reuses a code the
   runtime already has, and on its own separates the two live causes above --
   `30.04 s against a 30 s deadline` becomes readable from the receipt
   instead of from a capture harness.
2. **Then let the transport say the call was made and why it failed**, which
   is what AR-378 asked for and what the outside-in split cannot see.
   `failure_reason` today means "no call was made at all", and the stage acts
   on that meaning: it releases the call budget and does not set `called`
   (`inference.py:1702`). A timeout and an HTTP error did spend a call, so
   they cannot reuse that branch as written. Either carry an explicit
   "attempted" flag beside the reason, or add a second field for a failure
   after the request left; the invariant that `failure_reason` implies no
   call must stay true or move deliberately, not by accident.
3. **Name the causes from a closed vocabulary**, each returned as a result
   with an empty `value` rather than a bare `None`: the runtime deadline, an
   HTTP status the gateway returned (with the status on the attempt), a body
   that was not JSON, and model text that was not a JSON object. The last one
   is the sibling of `provider_response_truncated` and belongs beside it.
4. **Keep the blanket `except` blanket.** Nothing here should let an
   unexpected exception escape the transport; the change is to classify what
   is already caught, and to leave anything unrecognised on a residual code
   that is honestly distinct from the named ones.
5. **The ordering itself is operator configuration.** `timeout_ms` and the
   deployment timeout must be set so the runtime's deadline is the outer one,
   and the runtime cannot see the deployment's value to check it. What the
   runtime owes is the report: `agency doctor` should state each routed
   profile's effective timeout, so the comparison an operator has to make by
   hand today is at least made against a printed number.

Nothing here selects, ranks or filters a specialist. The change is in what
the runtime says about why a call it made did not come back.

## Dependencies

None. AR-388 (ADR-0204) supplies the `failure_reason` channel this extends
and the doctor-check precedent; AR-385 (ADR-0199) supplies the
result-instead-of-`None` precedent; AR-378 supplies the hiring loop's timing
and its standing request for the transport half. All three are merged.

## Acceptance

- [x] The staffing stage loop and the hiring stage loop classify an identical
      transport failure identically: a call aborted by the runtime's own
      deadline is `provider_call_timed_out` on both, distinct from every other
      transport failure, carrying the elapsed time and the configured timeout.
- [x] A non-2xx response from the gateway is recorded with its HTTP status
      instead of being discarded by the blanket `except`.
- [x] A complete body whose model text is not a JSON object is recorded as
      its own cause, distinct from both a truncated reply and a deadline
      abort, reproduced from the capture391 turn 206 body.
- [x] A transport failure after the request left spends its call budget and
      counts as `called`; a refusal before any call is made still releases
      the budget and does not, and `failure_reason` keeps one meaning.
- [x] `agency doctor` states the effective timeout of each routed workforce
      profile, shown live on the installed configuration.
