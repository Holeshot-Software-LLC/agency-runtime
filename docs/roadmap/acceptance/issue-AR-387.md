---
title: "AR-387 acceptance verification record"
status: active
category: roadmap
created: 2026-09-03
updated: 2026-09-03
tags: [acceptance, verification]
related:
  - docs/roadmap/issue-AR-387-recruiter-cards-carry-no-eligibility.md
  - docs/decisions/0203-show-the-recruiter-the-complete-eligible-card-set-per-unit.md
supersedes: []
superseded_by: null
type: acceptance-verification
issue_id: AR-387
candidate_commit: b349e59b4d27de609ea29a436273ff6353fe9800
evidence_cutoff: 2026-09-03
tracker_url: null
---

# AR-387 acceptance verification record

Verified on the second pass at `b349e59b`. Every `typed_recall` row the recruiter receives carries the
complete, identity-sorted list of detail cards the verifier's eligibility
admits for that unit and the count of eligible workers without a card; a
`staff_without_safe_team` repair contract names the eligible cards covering
each requirement the ranked executable team left uncovered; both recruiter
prompts state that a card outside the list can be forbidden or omitted but
never staffed. Criterion 4 is evidenced live on the same eleven install
wordings under strict mode against the reconciled store copy.

## Builder evidence

| Criterion | Kind | Artifact | Observed | Source |
|---|---|---|---|---|
| 1 | file | `_annotate_eligible_candidates gives each recall row eligible_candidate_ids, the verifier's eligibility over the detail cards, identity-sorted and complete for the unit, and eligible_candidates_without_card` | 2026-09-03 | `agency_runtime/core/workforce/inference.py:2352-2384` |
| 1 | file | `_recruit_ambiguous_plan annotates the rows once the detail cards are final, before the recruiter document is assembled` | 2026-09-03 | `agency_runtime/core/workforce/inference.py:3495-3505` |
| 1 | test | `test_every_recall_row_carries_the_complete_eligible_card_set asserts the plan unit lists exactly its two eligible planners, the implementation unit its one implementer, and an eligible worker without a card is counted rather than listed` | 2026-09-03 | `tests/test_recruiter_eligibility_view.py:189-211` |
| 1 | command-output | `eleven live turns: on all eight plan-authority units the recruiter ranked only cards inside eligible_candidate_ids, with six eligible cards listed each time` | 2026-09-03 | `docs/roadmap/acceptance/evidence/AR-387-evidence-20260903.txt:41-67` |
| 2 | file | `_eligible_coverers_by_requirement names the eligible detail cards covering each requirement, identity-sorted and bounded to eight, and nothing without a context` | 2026-09-03 | `agency_runtime/core/workforce/inference.py:2777-2811` |
| 2 | file | `_safe_team_repair_contract computes the coverers for what the ranked executable team left uncovered, falling back to what the required set leaves, and _SafeTeamRepairContract projects them as eligible_coverers_by_requirement` | 2026-09-03 | `agency_runtime/core/workforce/inference.py:2814-2874` |
| 2 | file | `_SafeTeamRepairContract carries eligible_coverers_by_requirement into the repair prompt beside the ranked candidates` | 2026-09-03 | `agency_runtime/core/workforce/inference.py:739-791` |
| 2 | test | `test_eligible_coverers_are_facts_not_a_ranking asserts identity order, eligibility, the card restriction, the empty cases and the bound` | 2026-09-03 | `tests/test_recruiter_eligibility_view.py:214-239` |
| 2 | test | `test_the_captured_blindness_is_repaired_with_the_eligible_coverer_named drives the captured turn-201 shape and asserts the repair contract names the eligible coverer of the missing domain and the corrected reply staffs it` | 2026-09-03 | `tests/test_recruiter_eligibility_view.py:308-403` |
| 3 | file | `_RECRUITER_SYSTEM states that eligible_candidate_ids is the complete list of cards the runtime can staff on the unit and that any other card can only be forbidden or omitted` | 2026-09-03 | `agency_runtime/core/workforce/inference.py:336-348` |
| 3 | file | `_RECRUITER_REPAIR_SYSTEM states that a card outside eligible_candidate_ids can only be forbidden or omitted for the unit, never staffed, and names eligible_coverers_by_requirement` | 2026-09-03 | `agency_runtime/core/workforce/inference.py:399-408` |
| 3 | file | `the staff_without_safe_team repair guidance says an excluded candidate can be neither required nor acceptable and points at the coverers` | 2026-09-03 | `agency_runtime/core/workforce/inference.py:223-234` |
| 3 | test | `test_both_prompts_state_the_eligibility_boundary pins the phrases in both prompts and the guidance` | 2026-09-03 | `tests/test_recruiter_eligibility_view.py:242-256` |
| 4 | command-output | `eleven live turns under strict mode: zero staff_without_safe_team on any unit, zero ranked cards outside eligible_candidate_ids on the eight plan-authority units, five turns completed against four on the previous run` | 2026-09-03 | `docs/roadmap/acceptance/evidence/AR-387-evidence-20260903.txt:41-67` |
| 4 | command-output | `the blindness as captured before the change: five staff_without_safe_team plan-unit failures across three runs, each with an eligible coverer unranked in the rows, and turn 201's document with 86 unflagged cards` | 2026-09-03 | `docs/roadmap/acceptance/evidence/AR-387-evidence-20260903.txt:6-25` |

## Verification

| Criterion | Verdict | Verifier run | Evidence digest | Observed | Reason |
|---|---|---|---|---|---|
| 1 | satisfied | `AR-387.1-20260903-b1d3e81d` | `6d2509fc7fcfb068560dc2f12ca6eae1793166c04fdb067971453762a5a05cd1` | 2026-09-03 | The inference.py excerpts show each plan-unit recall row receives a sorted verifier-eligible intersection with detail-card IDs plus the exact eligible-without-card count, and the cited test verifies both fields across units. |
| 2 | satisfied | `AR-387.2-20260903-b5d19e92` | `43e708770f46480e8075394d2ce095ae7da8537b9546b0d5f15c57328f8fa21f` | 2026-09-03 | The excerpts show the repair contract computes uncovered ranked-team requirements, maps each to eligible covering cards, exposes that map in the prompt, and a staff_without_safe_team test asserts the expected coverer. |
| 3 | satisfied | `AR-387.3-20260903-4e61b243` | `532da78bdafb5832dedbb9a83ff148926f03aa13b14c84d87e0cf0bf8a8405bd` | 2026-09-03 | The excerpts at inference.py:336-348 and 399-408 state for both recruiter prompts that cards outside eligible_candidate_ids can only be forbidden or omitted and cannot be selected or staffed. |
| 4 | satisfied | `AR-387.4-20260903-e19cca6e` | `6b5872f2abccf6d464710f469804dd0efde8194fddec5239fc38d085f4223996` | 2026-09-03 | The cited eleven-turn strict-mode summary reports zero staff_without_safe_team rejections on any unit, directly excluding the prohibited plan-authority outcome. |
