---
title: "Worklog detail: refuse an invented domain at the plan boundary"
status: active
category: worklog
created: 2026-08-15
updated: 2026-08-15
tags: [workforce, planning, staffing, recruiter, canary, evidence]
related:
  - docs/roadmap/issue-AR-253-dynamic-team-dispatch-on-every-harness.md
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/decisions/0118-require-inference-owned-staffing.md
  - docs/decisions/0132-fund-one-repair-per-workforce-inference-stage.md
  - agency_runtime/core/workforce/intent.py
  - agency_runtime/core/workforce/planning_contracts.py
supersedes: []
superseded_by: null
type: worklog
commit: 6e4908014968187bc190eef4de858d2adb3635cd
short: 6e490801
date: 2026-08-15
pr: null
related_issues:
  - docs/roadmap/issue-AR-253-dynamic-team-dispatch-on-every-harness.md
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
---

# Worklog detail: refuse an invented domain at the plan boundary

## Purpose

With the launcher republished and hooks staffing again, the live Claude canary
reached routing and died at `workforce_inference_failed` / `inference_invalid`.
Both recruiter attempts were rejected `provider_response_contract_invalid` with
one identical failure, `staff_without_safe_team`, on a single unit.

That code fires when the recruiter decided to staff but no team within
`max_selected_per_unit` covers the unit's requirements. Coverage is
**conjunctive** across six axes — artifact, lifecycle, domain, stack,
capability, authority — so one uncoverable axis defeats every possible ranking.
The recruiter was never going to succeed, and the funded retry could not help
because ADR-0132's repair prompt is addressed to the recruiter while the plan is
what is wrong.

Offline measurement against the live 283-contract roster showed the typed space
is healthy: a realistic review unit is staffable, and sweeping every
roster-declared value one axis at a time leaves 0 of 8 lifecycles, 0 of 8
artifact kinds and 0 of 4 authorities unstaffable. The fault had to be a value
the planner may emit that no contract declares.

## Approach

`parse_work_unit_plan` gained an optional `allowed_domains` vocabulary.
`compile_intent_plan` is the one boundary that knows the live roster, so it
supplies it; every other caller — `enrich_intent_plan`, the deterministic
fallback, the evals — omits it and keeps today's behaviour.

The refusal is a plain `ValueError` naming the offending domains, which matters
more than it looks: `_invoke_stage`'s generic repair branch keeps the planner's
own system prompt and embeds `_validation_detail(exc)` in the feedback, so the
correction goes to the component that made the mistake and tells it what the
mistake was.

Normalization still runs first. `_canonical_domain` rescues aliases and token
matches, and only what it could not place is refused, so the planner's working
vocabulary is not narrowed.

## Challenges encountered

The obvious version of this fix — refuse every domain no contract declares —
broke `test_open_ended_pool_can_declare_gap_without_inventing_a_roster_candidate`,
and that test is load-bearing. It plans `domains: ["quantum-build-systems"]`
with `novel_capability: "quantum-build-evaluation"` so the recruiter can answer
`inference-declared-gap`, which is the rule-6 contractor-hiring trigger.
`_validate_nomination_decisions` only rejects `staff` decisions, so an unknown
domain is a defect **only when the plan claims no novelty**. The shipped rule
keys on `novel_capability`, the contract's existing signal for work the
workforce genuinely lacks, matching how `capability_ids` are already
hard-validated with novelty carried in a dedicated field.

Second correction: the earlier diagnosis named `lifecycle_phase: coordination`
as a co-equal gap — enum-legal, declared by zero contracts. It cannot be the
live cause. The compact planner never chooses a lifecycle; `_unit_document`
derives it from the artifact through `_ARTIFACT_FACTS`, which yields only
discovery, design, documentation, implementation, planning, review and testing.
Domains were the only planner-chosen axis that could go off-vocabulary.

The default `_compile` fixture in `tests/test_workforce_intent.py` declared a
three-domain roster while its cases exercised `accessibility`, `product`,
`design`, `marketing` and `finance` — all real roster domains. The fixture was
widened to a slice of the real vocabulary; a fixture roster narrower than the
domains under test proves nothing about canonicalization.

## Decisions and alternatives

Two alternatives were recorded in AR-253 and rejected. **Giving uncoverable axes
the stack wildcard** would absorb the gap but weaken the sufficiency proof the
staffing verifier exists to make. **Routing the repair by fault**, planner versus
recruiter, is the most correct and the largest change; the boundary check makes
it less urgent because the structural case no longer reaches the recruiter.

Putting the roster's domains into the transport JSON schema as an enum was also
rejected: it would fail earlier but would stop `_canonical_domain` from ever
rescuing an alias such as `qa` or `gis`.

## Verification

- `tests/test_workforce_intent.py`, `tests/test_workforce_inference.py`,
  `tests/test_workforce_selection_safety.py`,
  `tests/test_workforce_dynamic_hiring.py`,
  `tests/test_workforce_staffing_foundation.py`,
  `tests/test_workforce_selection_eval.py` — 197 passed, 1 skipped.
- CI's fast production spine — 674 passed, 20 skipped.
- CI's AR-119 matrix evidence list — 670 passed.
- `scripts/verify_docs.py` — passed for 688 Markdown files.
- Offline probe against the live 283-contract roster: for the canary's own ask,
  `text-normalization`, `text-processing` and `string-handling` survive
  normalization verbatim and are coverable by no team of four, while
  `code-review`, `regression-testing`, `python-development` and `code-quality`
  are rescued into roster domains and stay accepted.

`tests/test_upstream_selection_eval.py` has two failures that predate this
change; a pristine worktree at `bd2a6323` reproduces both. They construct
`UnitRecruitment` with 20 positional values for a 17-field dataclass. That file
runs in no push-triggered CI list, which is how it stayed red behind a green
pipeline.

## Follow-ups

- The canary's actual plan is unrecoverable — `routing_intent` and
  `routing_cache` are empty, the workforce cache is in-process, and
  `preflight_failure_receipts.provider_attempts` records attempt metadata
  without response content. This fix is proven by mechanism, not by replaying
  the failure; the next live Claude canary is the real test.
  ([AR-253](../roadmap/issue-AR-253-dynamic-team-dispatch-on-every-harness.md))
- The preflight receipt should name **which requirement axis** was uncoverable,
  not just the unit. The axis names are a closed six-value vocabulary, so it
  costs no evidence bounding, and without it every recurrence needs the same
  offline reconstruction.
  ([AR-253](../roadmap/issue-AR-253-dynamic-team-dispatch-on-every-harness.md))
- Only `workflow_dispatch` runs the full suite; push events run the fast spine
  and the matrix-evidence list. Test files outside both can sit red unnoticed.
  ([AR-119](../roadmap/issue-AR-119-inference-first-workforce.md))
