---
title: "AR-437: Enforce the reviewer independence the plan calls for"
status: open
category: roadmap
created: 2026-09-10
updated: 2026-09-10
tags: [workforce, staffing, verifier, critic, reliability]
related:
  - docs/decisions/0249-enforce-the-reviewer-independence-the-plan-calls-for.md
  - docs/roadmap/issue-AR-433-name-the-neighbour-a-wrong-neighbour-veto-points-at.md
  - docs/roadmap/issue-AR-434-plan-policy-reads-a-handoff-request-as-a-code-mutation.md
  - docs/decisions/0200-bind-the-strict-critic-to-the-advisory-doctrine.md
  - docs/decisions/0213-the-verifier-judges-safety-retrieval-judges-fit.md
  - docs/roadmap/evidence/AR-433-install-liveness-20260910.json
supersedes: []
superseded_by: null
type: issue
epic: reliability
issue_id: AR-437
priority: p1
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/859
depends_on: []
blocks: []
---

# AR-437: Enforce the reviewer independence the plan calls for

## Problem

On the same ordinary-review request, observed on the critic route during the
2026-09-10 liveness runs, the strict critic vetoed the same team shape on some
host runs with `missing-lifecycle-assurance-the-plan-calls-for` and approved it
on others (the evidence file records packets by capture time, not by host). All five captured packets share one shape: an `analysis` unit in the
discovery phase plus a `review-report` unit in the review phase whose outcome
says "independently review" that analysis, and the recruiter staffed
`code-reviewer` on both units. The reviewer reviews its own work. The plan
calls for independence; the team does not have it; the critic is right when
it vetoes and lax when it approves, so the outcome is a coin flip on a plan
requirement the runtime never enforced.

The verifier's `_assurance` check requires independent assurance only for
`modify`-authority units, so it never looks at this shape, and its
`review_independence_class_reused` finding fires only on explicit review
relations. The recruiter contract states
`separate_independent_assurance_required` but nothing checks that a
review-report unit downstream of a unit is staffed by a worker not selected
on the reviewed unit when the eligible neighbourhood offers one; in every
vetoed packet `silent-failure-hunter` and `type-design-analyzer` were ranked
and eligible on the review unit.

## Current state

Repaired on branch `claude/ar437-reviewer-independence-20260910` per ADR-0249:
the verifier's `_reviewer_reuse` refuses a review-report unit staffed by a
worker selected on a unit it reviews as the repairable failure
`review_reviewer_reused` when an independent covering team can be derived
from the recruiter's own executable ranking, with repair feedback naming the
reused worker and the reviewed unit; when no such team exists the verifier
adds nothing. One adversarial review pass withdrew the first draft's
per-worker eligibility test and its widened advisory. Regressions reproduce
the captured shape, the finding's identity, the no-team case, an eligible but
insufficient candidate, a forbidden candidate, the timing predicate and an
independent team. Evidence: the critic packets summarised in
[AR-433-install-liveness-20260910.json](evidence/AR-433-install-liveness-20260910.json)
and their raw captures beside the install directory.

## Approach

At the verifier, when a review-authority `review-report` unit depends on a
unit and shares a selected worker (or independence class) with it, and the
unit's eligible neighbourhood holds another ranked eligible worker, raise a
repairable staffing verification failure (for example
`review_reviewer_reused`) with repair guidance naming the unit, so the
recruiter repairs the team before the critic sees it. Keep it advisory when no
eligible alternative exists, keep inference-only selection, and leave the
critic's ground unchanged: after the fix the critic should see a team that
either has the independence or provably could not.

## Dependencies

AR-433 supplies the captured packets. ADR-0213 keeps safety at the verifier and
fit at retrieval; independence of a required review is a composition property
the verifier already owns for modify-authority units.

## Acceptance

- [ ] A regression reproduces the captured shape (analysis plus dependent
      independent review, same worker on both, an independent covering team
      in the ranking) as a repairable verifier failure, and a shape with no
      such team stays staffable with no new finding.
- [ ] Focused staffing suites, the named fast checks and conformance pass with
      no change to inference-only selection, the critic contract or the
      receipts.
- [ ] One bounded fresh diagnostic on the exact ordinary-review request shows
      the review unit staffed independently of the analysis unit on at least
      one host, with tracker and worklog parity.
