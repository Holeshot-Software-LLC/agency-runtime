---
title: "AR-377: The hiring workforce payload is uncached and sent again to the critic"
status: done
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

Taken, in the order the filing set out, and still deliberately not "add a
cache".

**Step 1 (AR-376)** scoped the per-worker projection: 115,745 -> 44,067
prompt tokens for the generator.

**Step 2 is this change.** The critic no longer receives a second copy of the
roster. It receives `cited_workforce`: the full comparison row for exactly the
workers the candidate names — nearest workers, disabled covering workers,
closest workers, the amendment target, every relationship target — plus every
worker named by `verified_gap.coverage_rows`, in roster order.

The redundancy was real, not merely duplicated bytes. By the time the critic
runs, `_validated_candidate` has already:

- rejected deterministic duplicates, both by role identity
  (`_duplicate_role_identity`) and by axis subset (`_obvious_duplicate`);
- rejected relationship targets unknown to the roster
  (`contract_invalid:relationship_target_unknown`);
- and `_verified_gap_projection` has already computed, deterministically and
  over every worker, which workers cover which typed requirements and whether
  they are execution-eligible, with `coverage_rows_complete` flagging
  truncation.

So the roster was being sent so the critic could re-derive, by inference,
three things the runtime had already decided by rule. What genuinely remains
for the critic is whether the candidate's own comparison is honest — the
`_CRITIC_SYSTEM` clause about "closest_workers ... misrepresented (claimed
overlap that does not match the snapshot)" — and that needs the rows it cites,
not the other two hundred and seventy-nine. `_CRITIC_SYSTEM` now says exactly
that, including that `workforce_count` is the roster size it is not being
shown in full, so bounded evidence is not read as a bounded roster.

The isolated security reviewer has never carried worker rows (AR-238), and
`_safety_repair_context` already narrowed to four axes; this brings the critic
into line with both.

**Step 3, caching, is not needed here and is not done.** The two calls that
carried the roster now cost 49,408 tokens together, down from 231,682. A cache
keyed on roster content would still miss exactly when the roster changes,
which is when hiring runs, and provider-side prompt caching measured 0 cached
tokens on every call in this work. If it is ever wanted, it should be its own
filing against the generator call, which is now the only one paying roster
scale.

## Measured

One hire, on the shipped 291-worker roster, the two calls that carry the
roster. Both prompts built exactly as `hiring.py` builds them and posted to
their own configured routes:

| | generator | critic | total |
|---|---|---|---|
| before AR-376 | 115,745 | 115,937 | 231,682 |
| after AR-376 | 44,067 | 44,143 | 88,210 |
| after AR-377 | 44,067 | **5,341** | **49,408** |

4.69x below where this started; 1.79x below AR-376 alone. The cited rows cost
1,922 tokens (5,341 against 3,419 for a critic prompt carrying no worker rows
at all), against 40,840 for the second full copy. The third call, the isolated
security review, carries no worker rows and never did.

## Dependencies

- AR-376 sizes the payload and establishes which fields are load-bearing.

## Acceptance

- [x] Measured tokens for one complete hire, before and after, including the
      critic call. The table above; raw output in
      `docs/roadmap/acceptance/evidence/AR-377-evidence-20260902.txt`.
- [x] The critic no longer receives a redundant copy of evidence the
      generator already consumed. It receives `cited_workforce` instead, and
      the three deterministic rejections that made the full copy redundant are
      named above.
- [x] A regression test pins the per-hire call count and that the workforce
      is serialized at most once per call that genuinely needs it. Three cases
      in `tests/test_workforce_dynamic_hiring.py`: one hire makes exactly
      three calls and only the generator prompt carries every worker; an
      uncited, non-covering worker never reaches the critic; and every worker
      Agency's own coverage rows name does.
