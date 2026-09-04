---
title: "AR-389 acceptance verification record"
status: active
category: roadmap
created: 2026-09-04
updated: 2026-09-04
tags: [acceptance, verification]
related:
  - docs/roadmap/issue-AR-389-critic-judges-neighbours-it-cannot-see.md
  - docs/decisions/0205-show-the-critic-the-eligible-neighbourhood-it-judges-against.md
supersedes: []
superseded_by: null
type: acceptance-verification
issue_id: AR-389
candidate_commit: pending
evidence_cutoff: 2026-09-04
tracker_url: null
---

# AR-389 acceptance verification record

Pending draft. The strict critic's document carries, per plan unit, the
verifier's complete identity-sorted eligible candidate list with its count,
compact cards for the eligible workers the recruiter ranked or selected, and
whether the selected workers are the whole neighbourhood; the contract and
the prompt say a wrong-neighbour veto must name a card in that list. Criterion
4 is evidenced by offline replays of the three baseline vetoes and by the same
eleven install wordings run live under strict mode against the same reconciled
store copy as the baseline.

## Builder evidence

| Criterion | Kind | Artifact | Observed | Source |
|---|---|---|---|---|
| 1 | file | `_critic_eligible_neighbourhood gives the critic, per plan unit, the verifier's complete identity-sorted eligible candidate list with its count, compact cards for the eligible workers the recruiter ranked or selected, and whether the selected workers are the whole neighbourhood` | 2026-09-04 | `agency_runtime/core/workforce/inference.py:3843-3891` |
| 1 | file | `_critic_neighbourhood_card projects a contract to identity, archetype, authority, domains, two outcomes and two not_for lines` | 2026-09-04 | `agency_runtime/core/workforce/inference.py:3831-3840` |
| 1 | file | `_strict_critic places eligible_neighbourhood in the critic document beside the selected worker contracts` | 2026-09-04 | `agency_runtime/core/workforce/inference.py:3950-3952` |
| 1 | test | `test_the_critic_sees_the_complete_eligible_neighbourhood_per_unit asserts the eligible planner is the only id and the only card while the ranked but ineligible desktop engineer appears in neither, with the count and the whole-neighbourhood flag` | 2026-09-04 | `tests/test_critic_eligibility_view.py:82-103` |
| 1 | command-output | `the critic documents of the nine live turns that reached the critic carry eligible_neighbourhood per unit with the identity list, count, ranked eligible cards and the whole-neighbourhood flag, tabulated per turn` | 2026-09-04 | `docs/roadmap/acceptance/evidence/AR-389-evidence-20260904.txt:33-61` |
| 2 | file | `the identity list is bounded to 64 and the card list to 16, both identity-sorted` | 2026-09-04 | `agency_runtime/core/workforce/inference.py:3818-3828` |
| 2 | test | `test_unranked_eligible_cards_are_ids_only_and_the_bounds_hold drives a 70-planner roster: 64 ids with count 70, cards only for the ranked eligible workers, the ineligible ranked card absent` | 2026-09-04 | `tests/test_critic_eligibility_view.py:106-131` |
| 3 | file | `critic_contract carries wrong_neighbor_must_name_an_eligible_card and eligible_neighbourhood_is_complete_per_unit` | 2026-09-04 | `agency_runtime/core/workforce/inference.py:3923-3926` |
| 3 | file | `_CRITIC_SYSTEM says a card outside eligible_neighbourhood was ineligible and can never be the right neighbor, that a wrong-neighbor veto must point at a card in it, and that the ground cannot apply when the selected workers are the whole neighbourhood` | 2026-09-04 | `agency_runtime/core/workforce/inference.py:427-460` |
| 3 | test | `test_the_contract_and_the_prompt_state_the_neighbourhood_boundary pins the two contract keys and the prompt phrases` | 2026-09-04 | `tests/test_critic_eligibility_view.py:134-146` |
| 4 | command-output | `offline replays of the three baseline vetoes with the neighbourhood: the team holding the obvious eligible neighbour approved, the team missing it stayed vetoed, the plan-unit coin flip became six of six` | 2026-09-04 | `docs/roadmap/acceptance/evidence/AR-389-evidence-20260904.txt:19-29` |
| 4 | command-output | `live on the eleven wordings against the baseline: completed 6 against 5, critic vetoes 3 against 3 on different turns, both baseline vetoes now approvals, every veto naming an eligible card the recruiter left unselected` | 2026-09-04 | `docs/roadmap/acceptance/evidence/AR-389-evidence-20260904.txt:33-61` |
| 4 | command-output | `the document grows by the identity lists and the ranked cards within the stated bounds` | 2026-09-04 | `docs/roadmap/acceptance/evidence/AR-389-evidence-20260904.txt:30-32` |

## Verification

| Criterion | Verdict | Verifier run | Evidence digest | Observed | Reason |
|---|---|---|---|---|---|
