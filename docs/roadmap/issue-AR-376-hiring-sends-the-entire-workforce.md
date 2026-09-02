---
title: "AR-376: Hiring sends every worker's full contract, 132k tokens per call"
status: in_progress
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
| full record | 1,519 bytes per worker |
| `complete_workforce` as actually serialized | 441,982 bytes |
| `prompt_tokens` reported by litellm | **115,745** |
| the route's declared `max_input_tokens` | 32,768 |

The prompt is three and a half times the limit the route declares for itself.
That limit is not enforced — the backing model accepted all 115,745 tokens —
but nothing in the tree checks it either, so this silently depends on whichever
model happens to back `task-agency-hiring-generator-v2`.

This filing first recorded 463,254 bytes and 132,581 tokens. Those came from
`json.dumps` defaults, while `_json` serializes compactly, so the figures above
are the prompt as it is actually sent. The conclusion is unchanged.

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
`employment`. `composition` alone is 16.5% of the payload.

Cost also scales linearly with roster size, so each worker hired makes the
next hire more expensive.

## Approach

Taken. `hiring_workforce_projection` carries every worker, in roster order,
disabled included, on twelve axes. Each is one that the hiring decision, or a
rule that can reject it, actually reads:

| axis | read by |
|---|---|
| `agent_id` | the amend target, the relationship target, and `_duplicate_role_identity`'s self-skip |
| `display_name` | `_duplicate_role_identity` — the role-claim axis |
| `authority` | both deterministic duplicate rules |
| `enabled` | "if a disabled worker covers the gap, abstain" |
| `artifact_kinds`, `lifecycle_phases`, `domains`, `stacks`, `outcomes` | `_obvious_duplicate` |
| `capability_ids` | the gap comparison and amend-overlap |
| `scope_qualifiers` | how narrowly an incumbent already applies |
| `not_for` | the explicit exclusion that makes a hard negative hard |

**The field set proposed in this filing was wrong and is corrected here.** It
would have dropped `display_name`, `outcomes`, `lifecycle_phases` and
`stacks`. All four are axes of the runtime's own deterministic duplicate
rejection (`_obvious_duplicate` and `_duplicate_role_identity`). Dropping them
would leave the generator unable to predict a rejection it will then receive —
which is exactly how this roster grew two workers both named "Request
Clarification Specialist". Keeping them costs the projection its headline
ratio and buys back a decision the model can actually make.

Everything else — `composition`, `version`, `version_hash`, `worker_id`,
`audit`, `tool_classes`, `hosts`, `platforms`, `context_mode`,
`schema_version`, `archetype`, `origin`, `employment` — is provenance,
revision identity, or delivery mechanics that no duplicate or amend rule
reads.

Both prompts that carry the roster get the projection: the generator's
`complete_workforce` and the critic's `runtime_gap_evidence.complete_workforce`
are the same rows. `_safety_repair_context` already narrowed to four of these
axes and is unaffected. Both system prompts now say what a row is, so a
bounded row is not read as a bounded roster.

## Dependencies

- None. Found while exercising the hiring path end to end for a genuine gap.

## Acceptance

- [x] The hiring prompt carries every worker, including disabled, in a
      projection whose fields are each justified by duplicate detection or
      amend-overlap. The twelve axes and the rule each answers to are in the
      Approach table above and in the comment above
      `HIRING_WORKFORCE_PROJECTION_FIELDS`.
- [x] The measured `prompt_tokens` for a hire on the shipped roster is
      recorded before and after: **115,745 → 44,067**, a 2.63x reduction, and
      441,982 → 208,654 bytes, with the same 291 workers. Both payloads were
      built from the same work unit, verified gap and system prompt and posted
      back to back to the same route.
- [x] A regression test pins that the projection cannot silently regain the
      dropped fields, and that no worker is omitted. Four cases in
      `tests/test_workforce_dynamic_hiring.py` pin the exact field tuple, that
      every deterministic-duplicate axis survives, that each dropped name is
      absent from the projection but still present on the contract, that a
      disabled worker is carried, and that neither prompt contains an
      incumbent's revision identity.
