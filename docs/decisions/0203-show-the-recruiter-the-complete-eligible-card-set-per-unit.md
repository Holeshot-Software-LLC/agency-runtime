---
title: "Show the recruiter the complete eligible card set per unit"
status: accepted
category: decisions
created: 2026-09-03
updated: 2026-09-03
tags: [workforce, recruiter, staffing, inference]
related:
  - docs/roadmap/issue-AR-387-recruiter-cards-carry-no-eligibility.md
  - docs/roadmap/issue-AR-384-staff-decisions-die-on-uncoverable-typed-requirements.md
  - docs/roadmap/issue-AR-383-inferred-subject-context-fails-its-own-projection.md
  - docs/decisions/0118-require-inference-owned-staffing.md
  - docs/decisions/0198-waive-the-typed-requirements-the-roster-declares-but-cannot-serve.md
  - docs/decisions/0202-read-the-recruiter-reply-where-no-safety-property-lives.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
id: ADR-0203
type: decision
deciders: [owner]
---

# ADR-0203: Show the recruiter the complete eligible card set per unit

## Status

**Accepted 2026-09-03.** Item 3 of the AR-383 capsule's next package, filed
as AR-387.

## Context

The recruiter's document carries two views of the roster: bounded
`typed_recall` rows per unit, each candidate with `execution_eligible` and
its reasons, and `detail_cards`, the union of every unit's rows plus the
hybrid lane's additions, with name, outcomes, scope and `not_for` but no
authority and no eligibility. A card recalled for the implementation unit is
therefore present, rankable and unflagged for the plan unit, and the prompt
rightly says an absent row is not an exclusion. Live on 2026-09-03 the
recruiter ranked three modify-authority implementers as required on a
plan-authority install unit for exactly that reason and left the two eligible
planners declaring both of the unit's domains unranked; the unit failed
`staff_without_safe_team` twice and the turn died. Every plan-unit failure of
that code across three runs had an eligible coverer of the missing token
unranked in the rows.

ADR-0118 forbids deterministic code from ranking, recommending or filtering
candidates; eligibility is a hard boundary the verifier already enforces
after the fact. The gap is that the boundary was enforced but not shown.

## Decision

1. **Every recall row carries the complete eligible card set.** After the
   detail cards are final, `_annotate_eligible_candidates` gives each unit's
   `typed_recall` row `eligible_candidate_ids`: the verifier's own eligibility
   (`typed_staffing_ineligibility`) over the detail cards, complete for the
   unit and identity-sorted, plus `eligible_candidates_without_card`, the
   number of eligible workers the bounded recall did not card. It is a
   boundary, not a ranking: the recruiter still chooses among the eligible
   cards or declares a gap.
2. **The repair names eligible coverers.** `safe_team_contract` carries
   `eligible_coverers_by_requirement`: for each requirement the ranked
   executable team left uncovered (falling back to what the required set alone
   leaves when nothing ranked was executable), the eligible detail cards that
   cover it, identity-sorted and bounded to eight. The recruiter already saw
   each candidate's coverage in the rows; this reconnects the fact to the
   failure.
3. **Both prompts state the rule.** A card outside a unit's
   `eligible_candidate_ids` can be forbidden or omitted for that unit but
   never staffed, because the runtime cannot select it; an excluded candidate
   in the repair contract can be neither required nor acceptable.

Nothing is filtered, ranked or recommended; the cards stay complete and the
verifier's rule is unchanged.

## Consequences

- On the installed roster a plan or review unit's eligible card set is the
  whole eligible roster (6 to 20 cards); analysis and implementation units
  list 25 to 50 of 40 to 68. The lists add two to four kilobytes to a
  recruiter prompt of 67 to 82; the prompt is not bounded by
  `MAX_REQUEST_BYTES`, which bounds the user request.
- The captured turn-201 shape is repaired end to end in
  `tests/test_recruiter_eligibility_view.py`: the first prompt lists the two
  eligible planners, the repair names the coverer of the missing domain, and
  the corrected reply staffs it.
- Live re-measurement on the same eleven wordings is recorded in AR-387.
- The strict critic's run-to-run variance on an identical team, measured
  alongside, is small per prompt (six of six approvals on one captured prompt,
  five of six vetoes on another with the same team) and large across prompts.

## Alternatives

- **Add `authority` to each card and a prose compatibility table.** Compact,
  but the table has two read-only exceptions the prompt would have to teach,
  and host, platform and tool eligibility would still be invisible.
- **Filter ineligible cards out of the document per unit.** Cards are shared
  across units, and ADR-0118 forbids a deterministic filter that hides
  candidates.
- **List the eligible roster rather than the eligible cards.** The recruiter
  may rank only cards, so eligible workers without a card would be named and
  unusable; the count says how many there are instead.
- **Leave it to the repair.** The captured repair carried the same blindness
  and failed the same way.
