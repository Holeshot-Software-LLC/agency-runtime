---
title: "AR-438: Cap ordinary asks at two planned units"
status: open
category: roadmap
created: 2026-09-11
updated: 2026-09-11
tags: [workforce, planner, plan-policy, reliability]
related:
  - docs/decisions/0251-cap-ordinary-asks-at-two-planned-units.md
  - docs/roadmap/issue-AR-434-plan-policy-reads-a-handoff-request-as-a-code-mutation.md
  - docs/roadmap/issue-AR-437-enforce-reviewer-independence-the-plan-calls-for.md
  - docs/roadmap/issue-AR-433-name-the-neighbour-a-wrong-neighbour-veto-points-at.md
  - docs/roadmap/evidence/AR-437-live-proof-20260910.json
supersedes: []
superseded_by: null
type: issue
epic: reliability
issue_id: AR-438
priority: p1
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/867
depends_on: []
blocks: []
---

# AR-438: Cap ordinary asks at two planned units

## Problem

Under strict staffing the turns that die do so at the recruiter, and they die
on plan size. Since 2026-09-08 the most frequent recruiter rejection is
`missing_work_unit` (57 rows across recovered and failed turns, none of them
reply truncation): the recruiter answers a 56 KB prompt for a two-unit plan
and a 91 KB prompt for a six-unit plan and drops units under that load. The
second cause, `staff_without_safe_team` (14 rows), is coverage forcing on
units the request never needed. Of 88 completed plans, 33 carried three to
ten units; the one-paragraph review request that started this investigation
drew two to four units per host. Every extra unit multiplies both failures.

## Current state

Repaired on branch `claude/ar438-unit-ceiling-20260911` per ADR-0251:
`planning_unit_ceiling` in `plan_policy` returns 2 for every request the
policy does not itself expand (code mutation, security review, repository
mapping, regulated assurance), reusing the exact classification
`plan_policy_violations` applies, and the pipeline passes it to the planner as
`max_planned_units`. The activation canary and contextual-inquiry contracts
still take precedence. Regressions cover ordinary, documentation, merge,
install and question wordings, the expanding shapes, negated scope, and the
planning-options precedence.

## Approach

Decide the ceiling deterministically from the same request profile the
policy uses so the planner is never asked for a shape the policy would then
refuse: two units for an ordinary ask (the work and its review, or an install
and its verification), the existing limits otherwise. No fallback and no
change to inference-owned planning within the ceiling.

## Dependencies

AR-434 supplies the shared request classification. AR-437 and AR-433 remain
the gates that judge the smaller teams. The recruiter-batching lift for the
plans the policy does expand is a separate package.

## Acceptance

- [ ] `planning_unit_ceiling` returns 2 for the exact ordinary-review, merge,
      handoff, README and install wordings and None for code-mutation,
      security-review, repository-mapping and regulated-assurance wordings.
- [ ] The pipeline passes the ceiling as `max_planned_units` without
      overriding the activation-canary or contextual-inquiry contracts, and the
      focused and named fast checks pass.
- [ ] One fresh ordinary-review turn per host after the reinstall plans at
      most two units on every host, with the staffed rate recorded against the
      2026-09-11 pre-change batch.
