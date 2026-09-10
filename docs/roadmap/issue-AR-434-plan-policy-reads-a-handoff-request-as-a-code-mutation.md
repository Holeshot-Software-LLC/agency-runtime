---
title: "AR-434: Plan policy reads a handoff request as a code mutation"
status: open
category: roadmap
created: 2026-09-10
updated: 2026-09-10
tags: [workforce, planner, plan-policy, reliability]
related:
  - docs/roadmap/issue-AR-433-name-the-neighbour-a-wrong-neighbour-veto-points-at.md
  - docs/roadmap/issue-AR-415-respect-negated-change-requests.md
  - docs/decisions/0200-bind-the-strict-critic-to-the-advisory-doctrine.md
  - docs/roadmap/evidence/AR-433-critic-veto-population-20260910.json
supersedes: []
superseded_by: null
type: issue
epic: reliability
issue_id: AR-434
priority: p2
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/848
depends_on: []
blocks: []
---

# AR-434: Plan policy reads a handoff request as a code mutation

## Problem

Codex trace `01a08c99-d767-70c1-8d5a-a4d1171dc8ca` (2026-09-10) asked:
"can you create a handoff, ill let another agent crank on this for a bit,
include that observation, and where we left off and whats next to do, and
where the code is and what branch and anything it needs to start working on
this fresh". `plan_policy_violations` tokenizes that as mutation `create` plus
code `code` with no documentation token (`handoff` is not in `_DOCS`), so it
classifies the request as a code mutation and rejected the planner's first
plan with `plan_missing_implementation`, `plan_missing_test_implementation`
and `plan_missing_test_evidence_review`. The repaired plan carried the units
the validator demanded, and the strict critic then vetoed the team with
`missing-lifecycle-assurance-the-plan-calls-for`: the plan now called for
implementation and test lifecycle assurance that a handoff document neither
needs nor can be staffed for. The receipt is in the AR-433 population
evidence; the token classification reproduces deterministically from the
request text alone.

## Current state

Filed from the AR-433 investigation; no repair on this branch. The defect is
in the deterministic request classification, not in the planner, recruiter or
critic, and it turns one class of ordinary operational request into a
guaranteed veto.

## Approach

Bound the code-mutation trigger to requests whose mutation object is code,
not requests that merely mention where the code lives: treat handoff, note,
capsule, summary and similar prose artefacts as documentation tokens, and do
not let a locative "the code" alone satisfy `_CODE` beside a prose-object
mutation verb. Keep every existing negated-scope rule (AR-415), add the exact
observed wording as a regression with a code-mutation negative control, and
leave inference-only staffing, the independent critic and the validators
unchanged.

## Dependencies

AR-433 carries the observation and evidence. AR-415 governs the negated-scope
handling the same function applies.

## Acceptance

- [ ] The exact observed handoff wording is not classified as a code mutation
      and a genuine code-mutation request with the same verbs still is.
- [ ] Focused plan-policy regressions and the named fast checks pass with no
      change to inference-owned planning, staffing, critic or validator
      boundaries.
- [ ] One bounded fresh diagnostic on the exact wording reaches staffing
      without the three lifecycle repair codes, with tracker and worklog
      parity.
