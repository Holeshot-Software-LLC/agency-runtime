---
title: "AR-376: Hiring sends every worker's full contract, 132k tokens per call"
status: open
category: roadmap
created: 2026-09-02
updated: 2026-09-02
tags: [workforce, hiring, cost]
related:
  - docs/roadmap/issue-AR-377-hiring-payload-uncached-and-duplicated.md
  - docs/roadmap/issue-AR-378-hiring-failure-records-no-attempt.md
  - docs/roadmap/issue-AR-374-host-capability-vocabulary-gap.md
supersedes: []
superseded_by: null
type: issue
epic: workforce
issue_id: AR-376
priority: p1
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/550
depends_on: []
blocks: []
---

# AR-376: Hiring sends every worker's full contract, 132k tokens per call

## Problem

`hire_contractor_for_gap` serializes the complete roster into its prompt:

```python
workforce = [item.to_dict() for item in contracts]   # hiring.py:2009
```

`core/selector/pipeline.py` passes `active_snapshot.contracts`, so that is
every worker. Measured against the shipped 291-worker roster:

| | measured |
|---|---|
| full record | 1,455 bytes per worker |
| `complete_workforce` | 463,254 bytes |
| `prompt_tokens` reported by litellm, measured twice | **132,581** |
| the route's declared `max_input_tokens` | 32,768 |

The prompt is four times the limit the route declares for itself. That limit
is not enforced — the backing model accepted all 132,581 tokens — but nothing
in the tree checks it either, so this silently depends on whichever model
happens to back `task-agency-hiring-generator-v2`.

## Current state

Sending **all workers** is deliberate and should stay. `_HIRE_SYSTEM` tells
the generator to "independently compare the required capability against every
supplied worker, including disabled and non-active workers". Hiring cannot
delegate that to the recruiter, because:

- the recruiter only ever saw a bounded recall sample, capped by
  `MAX_HYBRID_DETAIL_CARD_BYTES`, and its own prompt says candidate rows are
  "a bounded coverage-first recall sample ... omission is not exclusion";
- recall skips disabled workers outright (`inference.py:1568`), while hiring
  must see them because `_HIRE_SYSTEM` says to abstain when a disabled worker
  covers the gap;
- amend-first (AR-240) needs the candidates the recruiter rejected.

Hiring is the last gate before a worker becomes permanent, so it is right not
to trust a bounded upstream sample.

Sending **all fields of** all workers is not deliberate. Duplicate detection
and amend-overlap cannot be informed by `version_hash`, `audit`,
`composition`, `worker_id`, `schema_version`, `archetype`, `origin` or
`employment`. Measured, scoping to identity, capability ids, domains,
artifact kinds, scope qualifiers, not-for, authority and enabled:

    full   463,254 bytes  (~115,813 tokens)
    scoped 137,132 bytes  (~34,283 tokens)   3.4x smaller

Cost also scales linearly with roster size, so each worker hired makes the
next hire more expensive.

## Approach

Not decided. The candidate is a bounded projection for the hiring and
hiring-critic prompts, carrying only what duplicate detection and
amend-overlap can actually use, with the field set justified rather than
guessed. Any change must preserve the completeness property above: every
worker still appears, including disabled ones.

## Dependencies

- None. Found while exercising the hiring path end to end for a genuine gap.

## Acceptance

- [ ] The hiring prompt carries every worker, including disabled, in a
      projection whose fields are each justified by duplicate detection or
      amend-overlap.
- [ ] The measured `prompt_tokens` for a hire on the shipped roster is
      recorded before and after.
- [ ] A regression test pins that the projection cannot silently regain the
      dropped fields, and that no worker is omitted.
