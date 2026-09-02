---
title: "AR-377: The hiring workforce payload is uncached and sent again to the critic"
status: open
category: roadmap
created: 2026-09-02
updated: 2026-09-02
tags: [workforce, hiring, cost, cache]
related:
  - docs/roadmap/issue-AR-376-hiring-sends-the-entire-workforce.md
  - docs/roadmap/issue-AR-378-hiring-failure-records-no-attempt.md
supersedes: []
superseded_by: null
type: issue
epic: performance
issue_id: AR-377
priority: p1
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/551
depends_on: []
blocks: []
---

# AR-377: The hiring workforce payload is uncached and sent again to the critic

## Problem

The 132,581-token workforce payload described in AR-376 is paid in full on
every hiring call, and paid twice per hire.

**Nothing caches it.** `workforce_cache_get` and `workforce_cache_put` are
used only for the planner (`inference.py:3455`, `:3481`) and the recruiter
(`:3146`, `:3206`). `core/workforce/hiring.py` contains no cache usage at
all; its only match for "cache" is the word "cache-busting" inside a prompt
string.

**No provider-level prompt caching.** `core/structured_provider.py` contains
no `cache_control`, no ephemeral blocks, and nothing equivalent.

Measured against litellm, sending the byte-identical payload twice back to
back:

    run 1: prompt_tokens=132,581  cached_tokens=1,280  (1.0% cached)
    run 2: prompt_tokens=132,581  cached_tokens=1,280  (1.0% cached)

An identical repeat call still reuses one percent of the prompt.

**It is sent twice per hire.** `_critic_prompt` (`hiring.py:798`) re-sends the
same payload to the hiring critic under `runtime_gap_evidence`.

`budget = _CallBudget(config.workforce.hiring_call_budget)` is constructed
once and shared across the generator, the critic and any repair, with a
default of 6. One hire is therefore up to six calls each carrying the full
roster: roughly **795k tokens to hire one worker**.

## Current state

Measured on this installation with a 291-worker roster. The figures above are
from two live calls against the configured route, not an estimate.

## Approach

Not decided, and deliberately not "add a cache". Any cache keyed on roster
content misses exactly when the roster changes, which is when hiring runs.
The order that makes sense is:

1. Scope the projection (AR-376), which cuts the payload 3.4x on its own.
2. Stop re-sending the workforce to the critic when the generator already
   proved the comparison, or send the critic only the rows its verdict needs.
3. Only then consider caching what remains, including provider-side prompt
   caching, which is currently unused everywhere.

## Dependencies

- AR-376 sizes the payload and establishes which fields are load-bearing.

## Acceptance

- [ ] Measured tokens for one complete hire, before and after, including the
      critic call.
- [ ] The critic no longer receives a redundant copy of evidence the
      generator already consumed, or the reason it must is recorded.
- [ ] A regression test pins the per-hire call count and that the workforce
      is serialized at most once per call that genuinely needs it.
