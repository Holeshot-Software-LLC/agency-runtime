---
title: "AR-389: The strict critic vetoes wrong neighbours it cannot see"
status: done
category: roadmap
created: 2026-09-04
updated: 2026-09-04
tags: [workforce, critic, staffing, inference, eligibility]
related:
  - docs/decisions/0205-show-the-critic-the-eligible-neighbourhood-it-judges-against.md
  - docs/decisions/0200-bind-the-strict-critic-to-the-advisory-doctrine.md
  - docs/decisions/0203-show-the-recruiter-the-complete-eligible-card-set-per-unit.md
  - docs/roadmap/issue-AR-386-strict-critic-vetoes-verifier-accepted-install-turns.md
  - docs/roadmap/issue-AR-387-recruiter-cards-carry-no-eligibility.md
  - docs/roadmap/issue-AR-383-inferred-subject-context-fails-its-own-projection.md
  - docs/roadmap/handoffs/issue-AR-383.md
supersedes: []
superseded_by: null
type: issue
epic: reliability
issue_id: AR-389
priority: p1
tracker_url: null
depends_on: []
blocks: []
---

# AR-389: The strict critic vetoes wrong neighbours it cannot see

## Problem

After ADR-0200 the strict critic vetoes on four grounds, the first being a
specific wrong-neighbour selection: a selected worker where a better-fitting
one existed. On the ADR-0203 run (2026-09-03, eleven install wordings, strict
mode) three verifier-accepted teams were lost to exactly that code, on turns
203, 205 and 208, and the critic's variance on an identical team was
measured at six approvals of six on one wording and one of six on another.

The critic's document carries the request, the plan, the proposal, the
verified staffing decision and the full contracts of the selected workers.
It carries nothing about who else the runtime could have staffed on each
unit. A wrong-neighbour veto is a claim that a better eligible card existed;
the critic can neither check that the card it has in mind was eligible for
the unit (an implementer on a plan unit is not) nor see the eligible cards
the recruiter ranked below the selection. The recruiter had the same
blindness until ADR-0203 gave it `eligible_candidate_ids` per unit.

## Current state

Offline replays of the three vetoed critic calls (raw389 captures, gateway
cache bypassed, six trials each) with a per-unit eligible neighbourhood added
to the document and one boundary sentence in the prompt:

| turn | team on the contested unit | fresh baseline approvals | with the neighbourhood |
|---|---|---|---|
| 205 | `operations-manager` on the plan unit | 0 of 3 (earlier 1 of 6) | 6 of 6 |
| 208 | `cross-platform-installer-engineer` and `devops-automator` on the helix unit | 1 of 3 | 3 of 6 to 6 of 6 across three shapes |
| 203 | `devops-automator` alone, the installer engineer ranked only acceptable | 2 of 3 | 0 of 6 |

The view makes the verdict evidence-based in both directions: the team that
holds the obvious eligible neighbour is approved, the team that left it
unselected stays vetoed, and the plan unit whose selection sat among six
eligible planners is no longer a coin flip. Full eligible sets reach 68 cards
on advise units, so an identity-sorted truncation of cards is not a faithful
boundary; the complete identity list is small and the compact cards belong
where the recruiter actually looked.

Live on the same eleven wordings with the view (2026-09-04): completed 6
against the baseline's 5; the critic reached 9 turns, approved 6 and vetoed
3, on different turns from the baseline's 3. Both baseline vetoes (203, 208)
are approvals with their obvious neighbours on the team; each remaining veto
names an eligible card the recruiter ranked and left unselected (the
cross-platform release verifier on 202 and 205, the infrastructure
maintainer and test automation engineer written into 209's codes). The
completion count is the same measurement within run-to-run variance; the
change is that every veto now points at a card the runtime could have
staffed.

## Approach

ADR-0205. The critic document gains `eligible_neighbourhood`, per plan unit:

1. `eligible_candidate_ids`: the verifier's eligibility over the enabled
   roster, complete for the unit and identity-sorted; its only bound is the
   roster's own size limit, so no unranked neighbour is ever cut from it;
   `eligible_count` carries the size.
2. `ranked_eligible_cards`: compact cards (identity, archetype, authority,
   domains, two outcomes, two `not_for` lines) for every eligible worker the
   recruiter ranked or selected on that unit, identity-sorted; the bound is
   the recruiter's own per-unit ranking bound, so no such worker is ever cut.
3. `selected_are_whole_neighbourhood`: whether the selected workers are every
   eligible card, in which case wrong-neighbour selection cannot apply.
4. `critic_contract` gains `wrong_neighbor_must_name_an_eligible_card` and
   `eligible_neighbourhood_is_complete_per_unit`; the system prompt says a
   card outside the list was ineligible and can never be the right
   neighbour, and that a wrong-neighbour veto must point at a card in it.

Nothing ranks, filters or staffs: the view is the verifier's own boundary,
stated to the stage that judges against it (ADR-0118 untouched).

## Dependencies

ADR-0203 (the recruiter's view of the same boundary). None blocking.

## Acceptance

- [x] The critic document carries, per plan unit, the complete identity-sorted
      eligible candidate list with its count, compact cards for every eligible
      worker the recruiter ranked or selected (the recruiter's own per-unit
      ranking bound bounds them), and whether the selected workers are the
      whole neighbourhood; ineligible ranked cards appear in neither list.
- [x] The identity list is bounded only by the roster's own size limit and
      the card list only by the recruiter's per-unit ranking bound, both by
      construction; a roster of seventy eligible workers lists all seventy.
- [x] The critic contract and the system prompt state that a wrong-neighbour
      veto must name a card in the unit's eligible neighbourhood and that a
      card outside it can never be the right neighbour.
- [x] Measured on the same eleven install wordings under strict mode against
      the same reconciled store copy as the ADR-0203 run: the critic's
      wrong-neighbour vetoes and the completed turns are recorded against the
      baseline of three vetoes and five completions.

**Verification (2026-09-04).** The record is frozen at `ecde6574`; the
isolated codex verifier returned satisfied on all four criteria on its fourth
pass (runs `AR-389.1-20260904-f81e3dec`, `AR-389.2-20260904-57c9029e`, `AR-389.3-20260904-9d9b5c2a`, `AR-389.4-20260904-9515af3e`). The first pass at `2c0fc40a`
found criterion 1 absent for want of the bounds citations; the second
contradicted a cap of 64 on the identity list against "complete"; the third
contradicted a bare 16 on the cards against "the workers the recruiter
ranked or selected". `1bf3858d` bounds the list by the roster's own limit
and `ecde6574` bounds the cards by the recruiter's own ranking limit, both
by construction. The issue is done.
