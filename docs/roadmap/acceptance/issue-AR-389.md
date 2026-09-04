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
candidate_commit: ecde657481611dafc8a31a4fb6043dbdc9902dad
evidence_cutoff: 2026-09-04
tracker_url: null
---

# AR-389 acceptance verification record

Verified on the fourth pass at `ecde6574`. The strict critic's document carries, per plan unit, the
verifier's complete identity-sorted eligible candidate list with its count,
compact cards for every eligible worker the recruiter ranked or selected, and
whether the selected workers are the whole neighbourhood; the contract and
the prompt say a wrong-neighbour veto must name a card in that list. Criterion
4 is evidenced by offline replays of the three baseline vetoes and by the same
eleven install wordings run live under strict mode against the same reconciled
store copy as the baseline.

## Builder evidence

| Criterion | Kind | Artifact | Observed | Source |
|---|---|---|---|---|
| 1 | file | `_critic_eligible_neighbourhood gives the critic, per plan unit, the verifier's complete identity-sorted eligible candidate list with its count, compact cards for every eligible worker the recruiter ranked or selected, and whether the selected workers are the whole neighbourhood` | 2026-09-04 | `agency_runtime/core/workforce/inference.py:3853-3901` |
| 1 | file | `the identity list is complete by construction (its only bound is MAX_ACTIVE_ROSTER_SIZE) and the cards cover every eligible worker the recruiter ranked or selected (their bound is MAX_NOMINATION_RANKED_PER_UNIT, the recruiter's own per-unit ranking bound from which the selection is drawn)` | 2026-09-04 | `agency_runtime/core/workforce/inference.py:3823-3838` |
| 1 | file | `MAX_NOMINATION_RANKED_PER_UNIT bounds the recruiter's ranked rows per unit in the nomination schema` | 2026-09-04 | `agency_runtime/core/workforce/inference.py:672-690` |
| 1 | file | `_critic_neighbourhood_card projects a contract to identity, archetype, authority, domains, two outcomes and two not_for lines` | 2026-09-04 | `agency_runtime/core/workforce/inference.py:3841-3850` |
| 1 | file | `_strict_critic places eligible_neighbourhood in the critic document beside the selected worker contracts` | 2026-09-04 | `agency_runtime/core/workforce/inference.py:3960-3962` |
| 1 | test | `test_the_critic_sees_the_complete_eligible_neighbourhood_per_unit asserts the eligible planner is the only id and the only card while the ranked but ineligible desktop engineer appears in neither, with the count and the whole-neighbourhood flag` | 2026-09-04 | `tests/test_critic_eligibility_view.py:85-106` |
| 1 | test | `test_unranked_eligible_cards_are_ids_only_and_the_list_is_complete drives a 70-planner roster: all seventy ids in identity order with eligible_count 70, a card for every ranked eligible worker, the ineligible ranked card absent` | 2026-09-04 | `tests/test_critic_eligibility_view.py:109-136` |
| 1 | test | `test_the_bounds_are_the_roster_limit_and_the_recruiter_ranking_limit pins the identity bound to the roster limit and the card bound to the nomination schema's per-unit ranking limit` | 2026-09-04 | `tests/test_critic_eligibility_view.py:139-147` |
| 2 | file | `the identity list's only bound is the roster's own size limit and the cards' only bound is the recruiter's per-unit ranking limit` | 2026-09-04 | `agency_runtime/core/workforce/inference.py:3823-3838` |
| 2 | file | `MAX_ACTIVE_ROSTER_SIZE is the roster limit the runtime already enforces` | 2026-09-04 | `agency_runtime/core/roster/limits.py:1-4` |
| 2 | file | `the nomination schema admits at most MAX_NOMINATION_RANKED_PER_UNIT ranked rows per unit` | 2026-09-04 | `agency_runtime/core/workforce/inference.py:672-690` |
| 2 | test | `test_the_bounds_are_the_roster_limit_and_the_recruiter_ranking_limit and test_unranked_eligible_cards_are_ids_only_and_the_list_is_complete pin both bounds and list all seventy eligible ids` | 2026-09-04 | `tests/test_critic_eligibility_view.py:109-147` |
| 3 | file | `critic_contract carries wrong_neighbor_must_name_an_eligible_card and eligible_neighbourhood_is_complete_per_unit` | 2026-09-04 | `agency_runtime/core/workforce/inference.py:3933-3936` |
| 3 | file | `_CRITIC_SYSTEM says a card outside eligible_neighbourhood was ineligible and can never be the right neighbor, that a wrong-neighbor veto must point at a card in it, and that the ground cannot apply when the selected workers are the whole neighbourhood` | 2026-09-04 | `agency_runtime/core/workforce/inference.py:428-461` |
| 3 | test | `test_the_contract_and_the_prompt_state_the_neighbourhood_boundary pins the two contract keys and the prompt phrases` | 2026-09-04 | `tests/test_critic_eligibility_view.py:150-162` |
| 4 | command-output | `offline replays of the three baseline vetoes with the neighbourhood: the team holding the obvious eligible neighbour approved, the team missing it stayed vetoed, the plan-unit coin flip became six of six` | 2026-09-04 | `docs/roadmap/acceptance/evidence/AR-389-evidence-20260904.txt:19-29` |
| 4 | command-output | `live on the eleven wordings against the baseline: completed 6 against 5, critic vetoes 3 against 3 on different turns, both baseline vetoes now approvals, every veto naming an eligible card the recruiter left unselected` | 2026-09-04 | `docs/roadmap/acceptance/evidence/AR-389-evidence-20260904.txt:33-61` |
| 4 | command-output | `the document grows by the identity lists and the ranked cards` | 2026-09-04 | `docs/roadmap/acceptance/evidence/AR-389-evidence-20260904.txt:30-32` |

## Verification

| Criterion | Verdict | Verifier run | Evidence digest | Observed | Reason |
|---|---|---|---|---|---|
| 1 | satisfied | `AR-389.1-20260904-f81e3dec` | `ade03124eee9890e8276234b0397012fa9febd9dcf36b2def75b2f2681d326c3` | 2026-09-04 | The cited implementation builds each unit’s sorted eligible IDs and count, filters ranked or selected cards through eligibility, uses recruiter and roster bounds, computes whole-neighbourhood equality, and the cited tests cover completeness, ordering, exclusion, cards, count, and flag. |
| 2 | satisfied | `AR-389.2-20260904-57c9029e` | `14c052a03dabf424476c9d66969a4a1a3f62a78f6580999a5f3e6425fa25a36e` | 2026-09-04 | The inference constants equal the roster limit and nomination maxItems bound, while the cited test verifies all 70 eligible planner IDs are listed and cards stay within the recruiter bound. |
| 3 | satisfied | `AR-389.3-20260904-9d9b5c2a` | `476ef40b22bab3c0a94cd38529b21e7ca15b79b593ea1ade145e785efee7739e` | 2026-09-04 | inference.py excerpts show both contract flags and the system prompt explicitly requiring an eligible-neighbourhood card and excluding outside cards, with a test pinning those statements. |
| 4 | satisfied | `AR-389.4-20260904-9515af3e` | `4bb5443c2bca3ea76306e9d68086c893fa4be7bd635153c4a986629452ee9d7c` | 2026-09-04 | The cited live-run record states the same eleven strict-mode wordings and store copy, then records the ADR-0203 baseline of three critic vetoes and five completions against the new run's three vetoes and six completions. |
