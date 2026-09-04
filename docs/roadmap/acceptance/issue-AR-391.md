---
title: "AR-391 acceptance verification record"
status: active
category: roadmap
created: 2026-09-04
updated: 2026-09-04
tags: [acceptance, verification]
related:
  - docs/roadmap/issue-AR-391-recruiter-prompt-misstates-how-its-ranking-becomes-the-team.md
  - docs/decisions/0207-tell-the-recruiter-how-its-ranking-becomes-the-team.md
supersedes: []
superseded_by: null
type: acceptance-verification
issue_id: AR-391
candidate_commit: pending
evidence_cutoff: 2026-09-04
tracker_url: null
---

# AR-391 acceptance verification record

Pending draft. The recruiter document's contract states how a ranking becomes
the team with the verifier's own numbers, each typed recall row names the
requirements exactly one eligible card covers, both prompts state the
derivation, and a whole-team verifier rejection hands the recruiter the team
the runtime derived beside a correction. Criterion 6 is evidenced by offline
replays of the two captured review-unit recruiter calls derived through the
runtime's verifier and by the same eleven install wordings run live under
strict mode against the same reconciled store copy as the ADR-0206 run.

## Builder evidence

| Criterion | Kind | Artifact | Observed | Source |
|---|---|---|---|---|
| 1 | file | `the response_contract states acceptable_candidates_join_only_for_typed_coverage, ranking_is_read_as_order_only, rank_score_step from _rank_score_step(config.workforce.min_margin), confidence_is_the_lowest_selected_rank_score, margin_is_against_the_best_alternative_team, minimum_confidence and minimum_margin from config.workforce` | 2026-09-04 | `agency_runtime/core/workforce/inference.py:3757-3772` |
| 1 | file | `_rank_score_step is the one function the scorer _calibrated_rankings uses for the step, so the number in the contract is the number the rank scores use` | 2026-09-04 | `agency_runtime/core/workforce/inference.py:2711-2729` |
| 1 | file | `the verifier takes a unit's confidence as the minimum rank score over selected and rejects below budget.min_confidence, the same config.workforce.min_confidence the contract states` | 2026-09-04 | `agency_runtime/core/workforce/staffing_verifier.py:1303-1303` |
| 1 | file | `staffing_budget_for_config binds the verifier's min_confidence and min_margin to config.workforce` | 2026-09-04 | `agency_runtime/core/workforce/inference.py:2699-2709` |
| 1 | test | `test_the_contract_states_the_derivation_with_the_verifier_s_own_numbers asserts every contract key and that the numbers equal the configuration and _rank_score_step` | 2026-09-04 | `tests/test_team_derivation_account.py:152-166` |
| 1 | test | `test_the_scorer_and_the_contract_share_one_rank_score_step asserts _calibrated_rankings scores 1.0, 0.9, 0.8, 0.7 and every score equals 1 - index * _rank_score_step` | 2026-09-04 | `tests/test_team_derivation_account.py:184-190` |
| 2 | file | `_annotate_eligible_candidates writes sole_eligible_coverers per recall row: every requirement whose eligible coverers among the detail cards number exactly one, from _eligible_coverers_by_requirement` | 2026-09-04 | `agency_runtime/core/workforce/inference.py:2586-2598` |
| 2 | file | `_eligible_coverers_by_requirement names the eligible detail cards covering each requirement from typed_staffing_coverage and typed_staffing_ineligibility, identity-sorted` | 2026-09-04 | `agency_runtime/core/workforce/inference.py:3003-3035` |
| 2 | test | `test_each_recall_row_names_the_requirements_only_one_eligible_card_covers asserts the review row names risk-analysis to the analyzer alone and the single-planner plan row names every requirement to that planner` | 2026-09-04 | `tests/test_team_derivation_account.py:169-181` |
| 2 | test | `the fixture: four reviewers eligible on the review unit, only test-results-analyzer covering risk-analysis` | 2026-09-04 | `tests/test_team_derivation_account.py:64-87` |
| 3 | file | `the recruiter prompt's classification account: required is the team, acceptable joins only as a typed-coverage complement in rank order and never for fit, ranking read as order alone, confidence is the lowest selected rank score, rank in team order, the sole coverer directly after the team it completes, Required is the team not an emphasis label` | 2026-09-04 | `agency_runtime/core/workforce/inference.py:374-402` |
| 3 | file | `the recruiter prompt's typed_recall account names sole_eligible_coverers as the card on every safe team` | 2026-09-04 | `agency_runtime/core/workforce/inference.py:347-352` |
| 3 | file | `the recruiter prompt's account of fit names not_for: a card whose not_for line names the unit's work is not a faithful owner` | 2026-09-04 | `agency_runtime/core/workforce/inference.py:329-333` |
| 3 | file | `the repair prompt states the same derivation and names typed_recall.sole_eligible_coverers` | 2026-09-04 | `agency_runtime/core/workforce/inference.py:435-443` |
| 3 | test | `test_both_prompts_state_how_the_ranking_becomes_the_team asserts each phrase in the recruiter prompt and the repair prompt and that the single-required instruction is gone` | 2026-09-04 | `tests/test_team_derivation_account.py:193-218` |
| 4 | file | `_DerivedTeamRow projects one rejected unit's derived team: selected, required, runtime_added_for_typed_coverage, confidence, margin and lowest_ranked_selected with rank and rank score` | 2026-09-04 | `agency_runtime/core/workforce/inference.py:999-1051` |
| 4 | file | `_STAFFING_VIOLATION_REPAIR_REQUIREMENTS names the correction for the five codes the recruiter can act on; codes outside it stay bare` | 2026-09-04 | `agency_runtime/core/workforce/inference.py:1053-1078` |
| 4 | file | `_StaffingVerificationError keeps the derived rows for the failed units and the thresholds` | 2026-09-04 | `agency_runtime/core/workforce/inference.py:1081-1120` |
| 4 | file | `_staffing_violation_feedback_row emits unit_id, code, required_correction when mapped and derived_team when derived` | 2026-09-04 | `agency_runtime/core/workforce/inference.py:931-944` |
| 4 | file | `the _StaffingVerificationError feedback carries those rows and team_derivation with the thresholds` | 2026-09-04 | `agency_runtime/core/workforce/inference.py:1585-1605` |
| 4 | file | `_verified_recruiter_proposal raises with every unit's derived row and the budget's minimums` | 2026-09-04 | `agency_runtime/core/workforce/inference.py:3661-3669` |
| 4 | test | `test_a_whole_team_rejection_shows_the_derived_team_and_the_correction asserts the feedback row's required_correction, the exact derived_team and team_derivation` | 2026-09-04 | `tests/test_team_derivation_account.py:221-264` |
| 4 | test | `test_every_named_correction_is_a_verifier_code_and_a_bare_code_stays_bare asserts the map is a subset of the verifier codes and plan_hash_mismatch is not in it; the inference suite's budget-rejection case asserts loaded_agent_budget_exceeded reaches the recruiter bare` | 2026-09-04 | `tests/test_team_derivation_account.py:267-269` |
| 5 | test | `the captured shape: the owner first and the sole coverer fourth, and the same team in team order` | 2026-09-04 | `tests/test_team_derivation_account.py:111-124` |
| 5 | test | `test_a_whole_team_rejection_shows_the_derived_team_and_the_correction drives the first shape to a selection_confidence_too_low rejection (confidence 0.7, the analyzer at rank 4) and the second to acceptance with confidence 0.9 and the team release-verifier, test-results-analyzer` | 2026-09-04 | `tests/test_team_derivation_account.py:221-264` |
| 5 | file | `_minimum_team_with_required: the required set first, complements only for uncovered requirements in rank order` | 2026-09-04 | `agency_runtime/core/workforce/staffing_verifier.py:654-682` |
| 5 | file | `_budgets rejects a unit whose confidence is below the minimum as selection_confidence_too_low` | 2026-09-04 | `agency_runtime/core/workforce/staffing_verifier.py:1086-1109` |
| 6 | command-output | `the mechanism read from capture391: the review units' sole coverer, the 209 rejection and repair inversion, the runtime facts the account states` | 2026-09-04 | `docs/roadmap/acceptance/evidence/AR-391-evidence-20260904.txt:8-22` |
| 6 | command-output | `offline replays of the captured 203, 209 and 305 recruiter calls, cache bypassed, three trials each, derived through the runtime's verifier: baseline 1 of 6 review-unit replies accepted; with the account and the sole-coverer fact 6 of 6, every 203 team holding the owner and the coverer; 305 unchanged` | 2026-09-04 | `docs/roadmap/acceptance/evidence/AR-391-evidence-20260904.txt:23-48` |
| 6 | command-output | `live on the eleven wordings against the ADR-0206 run on the same store copy: completed 9 against 4, critic reached 9, approved 9, vetoed 0 against 4, pre-critic losses 2 against 3, recorded per turn with the caveat that the planner wrote different plans this run` | 2026-09-04 | `docs/roadmap/acceptance/evidence/AR-391-evidence-20260904.txt:49-104` |

## Verification

| Criterion | Verdict | Verifier run | Evidence digest | Observed | Reason |
|---|---|---|---|---|---|
