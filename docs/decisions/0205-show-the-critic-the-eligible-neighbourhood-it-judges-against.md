---
title: "Show the critic the eligible neighbourhood it judges against"
status: accepted
category: decisions
created: 2026-09-04
updated: 2026-09-04
tags: [workforce, critic, staffing, inference, eligibility]
related:
  - docs/roadmap/issue-AR-389-critic-judges-neighbours-it-cannot-see.md
  - docs/roadmap/issue-AR-386-strict-critic-vetoes-verifier-accepted-install-turns.md
  - docs/decisions/0118-require-inference-owned-staffing.md
  - docs/decisions/0200-bind-the-strict-critic-to-the-advisory-doctrine.md
  - docs/decisions/0203-show-the-recruiter-the-complete-eligible-card-set-per-unit.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
id: ADR-0205
type: decision
deciders: [owner]
---

# ADR-0205: Show the critic the eligible neighbourhood it judges against

## Status

**Accepted 2026-09-04.** Item 2 of the AR-383 capsule's next package after
the AR-388 close, filed as AR-389.

## Context

The strict critic may veto a specific wrong-neighbour selection (ADR-0200).
Its document carries the plan, the proposal, the verified staffing decision
and the selected workers' contracts, and nothing about the other cards the
runtime could have staffed on each unit. On 2026-09-03 three of eleven
verifier-accepted install teams were vetoed as wrong neighbours, and an
identical team was approved six of six times under one wording and once in
six under another. The critic was being asked whether a better eligible card
existed while shown none of them; it could neither tell an ineligible
implementer from an eligible alternative nor see the eligible cards the
recruiter had ranked below its selection.

Replaying the three vetoed calls with a per-unit eligible neighbourhood added
(six trials each, gateway cache bypassed) approved the team that held the
obvious eligible neighbour, kept the veto on the team that had left it
unselected, and turned a plan-unit coin flip into six approvals of six. The
verdict became evidence-based in both directions.

## Decision

1. **The critic document carries `eligible_neighbourhood`, per plan unit.**
   `eligible_candidate_ids` is the verifier's own eligibility over the
   enabled roster, complete for the unit and identity-sorted, its only bound
   the roster's own size limit (`MAX_ACTIVE_ROSTER_SIZE`), with
   `eligible_count` carrying the size; `ranked_eligible_cards`
   carries compact cards (identity, archetype, authority, domains, two
   outcomes, two `not_for` lines) for the eligible workers the recruiter
   ranked or selected on that unit, identity-sorted and bounded to 16;
   `selected_are_whole_neighbourhood` says when no other eligible card exists.
2. **The contract and the prompt state the boundary.** `critic_contract`
   gains `wrong_neighbor_must_name_an_eligible_card` and
   `eligible_neighbourhood_is_complete_per_unit`; the system prompt says a
   card outside the list was ineligible for the unit and can never be the
   right neighbour, that a wrong-neighbour veto must point at a card in that
   unit's neighbourhood, and that when the selected workers are the whole
   neighbourhood the ground cannot apply.
3. **Nothing ranks.** The identity list is complete and identity-sorted; the
   compact cards are exactly the eligible cards the recruiter itself ranked or
   selected. The runtime still selects, ranks and staffs nothing (ADR-0118),
   and the critic still only vetoes (AR-306, AR-304 unchanged).

## Consequences

- A wrong-neighbour veto now has something to be about: the critic can check
  that its candidate was eligible and see how the recruiter ranked it. Vetoes
  that name a real eligible neighbour persist, which is the critic doing its
  job; vetoes that named an ineligible implementer dissolve.
- The critic prompt grows by the identity lists and the ranked cards, a few
  kilobytes on documents of thirteen to twenty; the identity list grows with
  the eligible set (68 ids on this roster's advise units), the cards are
  bounded, and the roster's own size limit bounds the whole.
- The recruiter (ADR-0203) and the critic now read the same boundary; a
  disagreement between them is about fit, not about who was eligible.
- Measured live on the eleven install wordings (2026-09-04): six completions
  against five, three vetoes against three on different turns, both earlier
  vetoes approved, and every veto naming an eligible card left unselected.
  The critic also wrote the named cards into its reason codes on one turn,
  which the closed code charset and the sixteen-code bound admit.

## Alternatives

- **Full compact cards for every eligible worker.** Rejected: advise units
  reach 68 eligible cards and an identity-sorted truncation shows an arbitrary
  subset as if it were the neighbourhood.
- **Only the cards the recruiter ranked.** Rejected: the recruiter can leave
  the right neighbour unranked (turn 201 under AR-387); the complete identity
  list keeps that neighbour nameable.
- **Cap the identity list at 64.** Rejected after the isolated verifier
  contradicted it: advise units on this roster already have 65 to 68
  eligible cards, and the ids a cap cuts are exactly the unranked
  neighbours the list exists to name.
- **Drop the wrong-neighbour ground.** Rejected: on turn 203 it named a real
  defect; the fix is to let the critic check its claim, not to remove it.
