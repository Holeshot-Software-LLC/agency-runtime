---
title: "AR-378: A failed hiring call records zero attempts, so the receipt has nothing to debug"
status: open
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

Not decided. The obvious shape is for `_invoke` to record an attempt on
failure as well as success, carrying at least the provider name, requested
model, elapsed time and failure class, matching what the workforce stages
already emit. Whether the failure class can be distinguished depends on what
`invoke_structured_provider_result` surfaces when it returns `None`, which
needs checking before promising a taxonomy.

## Dependencies

- None, though AR-376 and AR-377 are the failure this silence was hiding.

## Acceptance

- [ ] A failed hiring call records at least one attempt with provider,
      requested model, elapsed time and a distinguishable failure class.
- [ ] `hiring_inference_failed` no longer stands alone as the only evidence.
- [ ] A regression test pins that a failing provider yields a non-empty
      attempts tuple.
