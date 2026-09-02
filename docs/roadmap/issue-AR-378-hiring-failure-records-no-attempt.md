---
title: "AR-378: A failed hiring call records zero attempts, so the receipt has nothing to debug"
status: in_progress
category: roadmap
created: 2026-09-02
updated: 2026-09-02
tags: [workforce, hiring, observability, receipts]
related:
  - docs/roadmap/issue-AR-376-hiring-sends-the-entire-workforce.md
  - docs/roadmap/issue-AR-377-hiring-payload-uncached-and-duplicated.md
supersedes: []
superseded_by: null
type: issue
epic: observability
issue_id: AR-378
priority: p1
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/552
depends_on: []
blocks: []
---

# AR-378: A failed hiring call records zero attempts, so the receipt has nothing to debug

## Problem

When the hiring provider call fails, `_invoke` returns `(None, None)` and no
attempt is recorded:

```python
        result = invoker(provider, prompt, schema, system_prompt=system, timeout=provider.timeout)
        if result is not None:
            return result, _attempt(stage, provider, result)
    return None, None            # hiring.py:714
```

The caller turns that into a bare abstention:

```python
    if result is None or hire_attempt is None:
        return ContractorHiringOutcome("abstained", ("hiring_inference_failed",))
```

Observed on this installation:

    status         = abstained
    reason_codes   = ('hiring_inference_failed',)
    attempts       = ()
    notification   = ''
    worker         = None
    contract       = None

## Current state

`hiring_inference_failed` is indistinguishable across every cause: provider
unreachable, timeout, schema rejection, transport error, oversized prompt.
There is no attempt row, no requested model, no validation detail and no
elapsed time.

The workforce stages do this properly. Each records a
`WorkforceInferenceAttempt` per try carrying stage, status, reason code,
requested model and validation detail, all readable straight off the receipt;
that is what made AR-373 and AR-374 tractable.

The gap cost real diagnostic time here. The abstention first looked like a
missing provider, then like a zero call budget (it is 6), then like a wrong
model name (`task-agency-hiring-generator-v2` is served). The actual cause was
found only by calling the provider directly outside the runtime and comparing
prompt sizes. None of that was visible from the receipt.

## Approach

Taken. The filing asked for `invoke_structured_provider_result` to be checked
before promising a taxonomy. It was: that function returns a bare `None` for
every cause -- unusable prompt, unserializable schema, non-positive timeout,
transport error, deadline, schema rejection -- and surfaces nothing else. No
taxonomy can be read off it. So the recorded failure class is confined to what
`_invoke` witnesses for itself, and hiring does not guess at the rest.

`_invoke` now returns `(result, applied_attempt, failures)`. Every try that
produced no structured result is recorded as a `HiringInferenceAttempt`
carrying stage, provider, requested model, elapsed milliseconds, a status and
a reason code, in the `WorkforceInferenceAttempt` vocabulary:

| reason code | status | what was witnessed |
|---|---|---|
| `provider_call_failed` | `failed` | a call was made, nothing came back |
| `provider_call_timed_out` | `failed` | the same, at or past its own deadline |
| `provider_prompt_exceeds_transport_limit` | `skipped` | over `MAX_STRUCTURED_PROMPT_BYTES`; no call is possible |
| `hiring_call_budget_exhausted` | `skipped` | the budget ended the chain first |

`provider_call_timed_out` is a fact, not an inference: the deadline handed to
the transport is `_bounded_timeout(provider.timeout)`, which only ever lowers
it, so an elapsed time at or past `provider.timeout` means the call spent its
whole deadline.

Failures that precede a success in the same chain are recorded too, so a hire
that only succeeded on its fallback says so.

Two consequences were handled rather than left implied:

- **Durable model evidence stays applied-only.**
  `_commit_pending_hiring_evidence` (`core/store/preflight.py`) replays each
  receipt as `record_model_receipt(status="success")`, so a failed try in that
  list would assert a model that never answered. The failure rows live on the
  outcome, not in `model_evidence`.
- **`calls_used` counts spent calls.** `_hiring_event`
  (`core/selector/pipeline.py`) excludes `skipped` attempts, which spend none.

Finer causes stay unavailable. Separating transport error from schema
rejection requires `invoke_structured_provider_result` to report why it gave
up; that is a change to its contract and belongs to its own filing.

## Dependencies

- None, though AR-376 and AR-377 are the failure this silence was hiding.

## Acceptance

- [x] A failed hiring call records at least one attempt with provider,
      requested model, elapsed time and a distinguishable failure class.
- [x] `hiring_inference_failed` no longer stands alone as the only evidence.
      The abstention now reads
      `reason_codes=('hiring_inference_failed', 'provider_call_failed')` with
      the stable stage code still first, and one attempt behind it.
- [x] A regression test pins that a failing provider yields a non-empty
      attempts tuple. Seven cases in
      `tests/test_workforce_dynamic_hiring.py` cover both failure statuses,
      both skip classes, the applied-only receipt filter and the `calls_used`
      count.
