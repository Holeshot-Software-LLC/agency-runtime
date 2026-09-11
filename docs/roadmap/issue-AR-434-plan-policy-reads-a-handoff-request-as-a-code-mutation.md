---
title: "AR-434: Plan policy reads a handoff request as a code mutation"
status: open
category: roadmap
created: 2026-09-10
updated: 2026-09-11
tags: [workforce, planner, plan-policy, reliability]
related:
  - docs/decisions/0250-read-a-prose-artefact-request-as-documentation-work.md
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

Merged in PR #866 (merge commit `5a1e6b3a`) per ADR-0250 and live on every
host at runtime digest `98f5ddda00ce`; the fresh diagnostic on the exact
handoff wording is still owed: `prose_artifact_request` in `plan_policy` reads a request that names
a prose artefact as the object of every change verb, whose only code nouns
are locative and which carries no strong code verb, as documentation work;
the policy and the deterministic planner call the predicate on the same text,
and the planner's acceptance contract lists the artefacts with the guard. The
exact observed wording now plans as documentation plus review and passes the
policy; a change verb whose object is the code, a strong code verb, a
non-locative code object and the mixed "update the code and the docs" case
keep the code shape; the negated-scope handling still runs first. One
adversarial review pass withdrew the first draft's bag-of-tokens form, which
had turned "update the auth code and add a note" into documentation work;
a second pass aligned the negation order for both readers and bound the prose
noun to its phrase; a third pass made the rule read multi-line and bulleted
asks. Follow-up recorded, not repaired here: a code change phrased with a verb
outside the policy's vocabulary beside a prose ask ("create a handoff and
harden the credential code") reads as documentation; widening the strong
code verbs is a vocabulary decision for its own amendment. The defect was in the deterministic request classification, not
in the planner, recruiter or critic.

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
