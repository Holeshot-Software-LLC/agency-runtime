---
title: "AR-391: The recruiter's prompt misstates how its ranking becomes the team"
status: in_progress
category: roadmap
created: 2026-09-04
updated: 2026-09-04
tags: [workforce, recruiter, staffing, inference, verifier]
related:
  - docs/decisions/0207-tell-the-recruiter-how-its-ranking-becomes-the-team.md
  - docs/decisions/0203-show-the-recruiter-the-complete-eligible-card-set-per-unit.md
  - docs/decisions/0206-show-every-outcome-on-the-card.md
  - docs/decisions/0118-require-inference-owned-staffing.md
  - docs/roadmap/issue-AR-390-recruiter-cards-hide-the-outcomes-that-name-the-work.md
  - docs/roadmap/issue-AR-389-critic-judges-neighbours-it-cannot-see.md
  - docs/roadmap/issue-AR-383-inferred-subject-context-fails-its-own-projection.md
  - docs/roadmap/handoffs/issue-AR-383.md
supersedes: []
superseded_by: null
type: issue
epic: reliability
issue_id: AR-391
priority: p1
tracker_url: null
depends_on: []
blocks: []
---

# AR-391: The recruiter's prompt misstates how its ranking becomes the team

## Problem

After ADR-0206 the strict critic's remaining vetoes on the eleven install
wordings sat on the review units of turns 203 and 209 and the plan unit of
305 (capture391, 2026-09-04). On both review units the runtime had selected
`test-results-analyzer` alone with `code-reviewer`, `reality-checker` and the
release verifier left ranked; the critic vetoed both teams as wrong-neighbour
selections, and it was right about the fit.

The recruiter did not choose that team. On 209 its first reply required the
release verifier on the review unit and ranked the analyzer fifth; the
verifier rejected the whole reply as `selection_confidence_too_low` and the
repair, told nothing but the code, inverted the team. On 203 the first reply
already required the analyzer alone. Replayed with the gateway cache bypassed
(three trials each), the recruiter required the release verifier, the reality
checker or the code reviewer on the review unit in six of six trials and never
the analyzer; pushed through the runtime's own proposal builder and verifier,
four of those six replies die as `selection_confidence_too_low`, one has no
safe team, and one passes only because the analyzer happened to land at rank
two.

Three runtime facts explain it, and none of them was stated to the recruiter:

1. **Acceptable candidates join the team only for typed coverage.** The
   derived team is every required candidate plus, only when a typed
   requirement is still uncovered, the fewest acceptable candidates in rank
   order that cover it (`_minimum_team_with_required`). Nothing is added for
   fit. On the review units `capability:risk-analysis` is covered by exactly
   one eligible card, the analyzer, so every safe team holds it; a required
   analyzer covers everything and every acceptable card is redundant, which is
   how 203 staffed it alone.
2. **The ranking is read as order alone.** `_calibrated_rankings` replaces the
   recruiter's scores with rank scores: rank one is 1.0 and each later rank is
   one step lower (the configured margin, at least 0.01). A unit's confidence
   is the rank score of its lowest-ranked selected worker, a runtime-added
   coverage complement included, and the verifier rejects the unit below the
   configured minimum. At the installed thresholds (step 0.1, minimum 0.8) a
   coverage complement at rank four sinks any team.
3. **A whole-team rejection reaches the recruiter as a bare code.** The
   feedback was `{"code": "selection_confidence_too_low", "unit_id": ...}`
   with a generic required action; the nomination repair, by contrast, carries
   a correction sentence and a safe-team contract per failed unit.

The prompt said the opposite of the first fact: an acceptable candidate was "a
valid alternative or complement that the runtime may add when needed", and
"Do not label every strong candidate required" taught the single-required
pattern. The prompt named no score rule and no confidence rule. The contract
carried `acceptable_candidates_are_optional` and nothing about coverage, rank
scores or thresholds.

The plan unit of 305 is a different loss. The recruiter required
`operations-manager` in six of six cache-bypassed trials, with and without the
account below, against the card's own `not_for` line ("the request requires
live operational changes"); every one of those teams passes the verifier and
the critic vetoed the live one preferring the site reliability engineer. The
prompt's account of fit named outcomes and scope and not `not_for`; naming it
is right and changed nothing measured, so the plan-unit residue is recorded
here as a roster-fit question for plan-authority host-side units, not as a
defect this issue fixes.

## Mechanism

Traced on capture391 and reproduced offline against the reconciled store
copy (generation 307, 291 contracts):

- `core/workforce/staffing_verifier.py::_minimum_team_with_required`: the
  required set first; complements only for requirements it leaves uncovered,
  smallest combination in rank order.
- `core/workforce/inference.py::_calibrated_rankings`: rank scores from
  `max(minimum_margin, 0.01)`; `build_verified_proposal` takes a unit's
  confidence as the minimum rank score over `selected` and its margin
  against the best alternative team.
- `core/workforce/staffing_verifier.py::_budgets`: `selection_confidence_too_low`
  when `row.confidence < budget.min_confidence`.
- `core/workforce/inference.py::_semantic_retry_prompts`: the
  `_StaffingVerificationError` branch emitted unit id and code only.

Typed recall on the review unit (turns 203 and 209): nine eligible cards;
`capability:risk-analysis` covered by `test-results-analyzer` alone. The
recruiter's faithful replies, derived offline (baseline, cache bypassed):

| turn, trial | review unit as returned | derived | verifier |
|---|---|---|---|
| 203.1 | verifier required, analyzer 4th | (other unit) | `invalid_ranking` |
| 203.2 | verifier, reality checker required, analyzer 4th | + analyzer, confidence 0.7 | `selection_confidence_too_low` |
| 203.3 | reality checker required, analyzer 2nd | + analyzer, confidence 0.9 | accepted |
| 209.1 | verifier required, analyzer 5th | + analyzer, confidence 0.6 | `selection_confidence_too_low` |
| 209.2 | code reviewer required, analyzer unranked | no safe team | `staff_without_safe_team` |
| 209.3 | verifier required, analyzer 4th | + analyzer, confidence 0.7 | `selection_confidence_too_low` |

## Current state

Fixed on the branch under ADR-0207: the contract carries the derivation with
the verifier's own numbers, each recall row names the requirements exactly one
eligible card covers, both prompts state the derivation and the fit account
names `not_for`, and a whole-team rejection shows the derived team beside a
correction. Offline replays with the prompt account alone: 203 accepted by the
verifier in three of three trials (one of three at baseline), 209 still none
of three because the recruiter left the sole coverer unranked twice and at
rank five once; the `sole_eligible_coverers` fact was added for exactly that.
The replays with the fact and the live run on the eleven wordings are recorded
in the acceptance evidence file.

## Approach

State the derivation where the recruiter reads it, with the runtime's numbers
rather than a paraphrase, and hand a whole-team rejection back with the team
the runtime derived. The verifier, the scorer and the selection derivation do
not change: the recruiter is the selection authority (ADR-0087, ADR-0118) and
the fix is to tell it the rule it is held to, not to select around it.

## Acceptance

- [ ] The recruiter document's `response_contract` states that acceptable
      candidates join only for typed coverage, that the ranking is read as
      order alone, the rank score step, that a unit's confidence is its lowest
      selected rank score, and the verifier's minimum confidence and margin,
      with every number taken from the same configuration and scorer the
      verifier applies.
- [ ] Each typed recall row names, per requirement, the single eligible card
      that covers it when exactly one does (`sole_eligible_coverers`),
      computed from the verifier's own eligibility and coverage over the
      detail cards.
- [ ] Both the recruiter prompt and the repair prompt state the derivation:
      required is the team, an acceptable candidate joins only as a
      typed-coverage complement in rank order and never for fit, a unit's
      confidence is the rank score of its lowest-ranked selected worker, rank
      in team order with the sole coverer directly after the team it
      completes; and the recruiter prompt's account of fit names the `not_for`
      line.
- [ ] A whole-team verifier rejection's feedback carries, per violated unit,
      the correction the recruiter can make and the derived team (selected,
      required, runtime-added coverage complements, confidence, margin, the
      lowest-ranked selected worker with its rank and rank score) with the
      thresholds, and a code outside the correction map reaches the recruiter
      bare as before.
- [ ] A regression test drives the captured shape, the owner ranked first and
      the sole coverer fourth, to a `selection_confidence_too_low` rejection
      whose feedback shows the derived team, and the same team ranked in team
      order is accepted with confidence 0.9.
- [ ] Offline replays of the captured 203 and 209 recruiter calls with the
      gateway cache bypassed, derived through the runtime's verifier, and the
      eleven install wordings run live under strict mode against the same
      reconciled store copy as capture391, are recorded per turn in the
      evidence file with the baseline beside them.
