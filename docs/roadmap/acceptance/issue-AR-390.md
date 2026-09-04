---
title: "AR-390 acceptance verification record"
status: active
category: roadmap
created: 2026-09-04
updated: 2026-09-04
tags: [acceptance, verification]
related:
  - docs/roadmap/issue-AR-390-recruiter-cards-hide-the-outcomes-that-name-the-work.md
  - docs/decisions/0206-show-every-outcome-on-the-card.md
supersedes: []
superseded_by: null
type: acceptance-verification
issue_id: AR-390
candidate_commit: 15c404f374ec1d5c59bc58f7b65a52304d7eb8be
evidence_cutoff: 2026-09-04
tracker_url: null
---

# AR-390 acceptance verification record

Verified on the second pass at `15c404f3`. The compact recruiter card and the critic's neighbourhood card
carry every outcome and every `not_for` line the contract declares, bounded
only by the contract's own limits; a recruiter document built for a
five-outcome contract shows all five on the detail card and the critic
document shows the same five. Criterion 4 is evidenced by offline replays of
the two captured recruiter calls and by the same eleven install wordings run
live under strict mode against the same reconciled store copy as the
ADR-0205 run.

## Builder evidence

| Criterion | Kind | Artifact | Observed | Source |
|---|---|---|---|---|
| 1 | file | `_compact_recruiter_card carries every outcome, every scope qualifier and every not_for line the contract declares; no card-side truncation remains` | 2026-09-04 | `agency_runtime/core/workforce/inference.py:2367-2385` |
| 1 | file | `MAX_OUTCOMES is the contract's own bound on outcomes and therefore the only bound on the card` | 2026-09-04 | `agency_runtime/core/workforce/contract.py:30-30` |
| 1 | test | `test_the_recruiter_card_carries_every_outcome_and_not_for_line asserts a five-outcome contract's card lists all five and both not_for lines` | 2026-09-04 | `tests/test_card_outcomes_complete.py:53-61` |
| 1 | test | `test_the_contract_bound_is_the_only_bound_on_a_card_s_outcomes asserts a contract with MAX_OUTCOMES outcomes shows all of them` | 2026-09-04 | `tests/test_card_outcomes_complete.py:74-79` |
| 2 | file | `_critic_neighbourhood_card carries the same outcomes and not_for lines` | 2026-09-04 | `agency_runtime/core/workforce/inference.py:3852-3864` |
| 2 | test | `test_the_critic_card_carries_the_same_outcomes_and_not_for_lines asserts the critic card lists all five outcomes and both not_for lines` | 2026-09-04 | `tests/test_card_outcomes_complete.py:64-71` |
| 3 | test | `test_the_recruiter_document_shows_every_outcome_on_the_detail_card drives planner, recruiter and critic on a roster whose contract declares five outcomes and asserts the recruiter's detail card and the critic's neighbourhood card both show all five` | 2026-09-04 | `tests/test_card_outcomes_complete.py:82-130` |
| 3 | test | `the fixture: _OUTCOMES declares the release verifier's five outcomes and _verifier builds the contract that declares them, so the detail card and the neighbourhood card are compared against five declared outcomes` | 2026-09-04 | `tests/test_card_outcomes_complete.py:36-50` |
| 3 | command-output | `the four tests in tests/test_card_outcomes_complete.py passed under -W error alongside the affected suites, the spine and the conformance eval` | 2026-09-04 | `docs/roadmap/acceptance/evidence/AR-390-evidence-20260904.txt:60-65` |
| 4 | command-output | `offline replays of the two captured recruiter calls with every outcome on every card: the release verifier required three of three on turn 202 against two of three at baseline, one of three on turn 205 against none` | 2026-09-04 | `docs/roadmap/acceptance/evidence/AR-390-evidence-20260904.txt:23-30` |
| 4 | command-output | `live on the eleven wordings against the ADR-0205 run: the release verifier on the verification unit in 7 of 8 critic-reached turns against 5 of 9; completed 4 against 6 with three pre-critic losses and four vetoes on other units, recorded per turn` | 2026-09-04 | `docs/roadmap/acceptance/evidence/AR-390-evidence-20260904.txt:31-59` |
| 4 | command-output | `the cut as the recruiter saw it and the roster's outcome counts` | 2026-09-04 | `docs/roadmap/acceptance/evidence/AR-390-evidence-20260904.txt:7-22` |

## Verification

| Criterion | Verdict | Verifier run | Evidence digest | Observed | Reason |
|---|---|---|---|---|---|
| 1 | satisfied | `AR-390.1-20260904-99046fe2` | `a597eed4a6d284832c879290065e99ffff8c1d90d0f0b1ebe47a27ae163daf5c` | 2026-09-04 | The cited implementation copies all contract outcomes and not_for lines without truncation, and the cited tests assert full preservation including all eight MAX_OUTCOMES entries. |
| 2 | satisfied | `AR-390.2-20260904-4ab0b1ec` | `7ce39b48431e35faaff2172ee440727a385a697572b7548beb5607c05eaef8ea` | 2026-09-04 | The cited function copies contract.outcomes and contract.not_for into the critic neighbourhood card, and the cited test asserts both fields match the verifier’s complete expected values. |
| 3 | satisfied | `AR-390.3-20260904-25596405` | `1bc4184fab05e323c3ae8f250ca3ddba0332df0df8c45e04122b40745d941454` | 2026-09-04 | The test fixture declares five outcomes, and the passing recruiter/critic test asserts both the operations-manager detail card and neighbourhood card contain exactly all five. |
| 4 | satisfied | `AR-390.4-20260904-479476df` | `f11bd05de7567378434e6c0cd0fbb2beb265a963df7b94a71b433a6e0001de9d` | 2026-09-04 | AR-390 evidence lines 31-59 identify the same eleven strict-mode wordings and store copy, record completed turns and per-turn verification-unit rankings, and compare them with the ADR-0205 run. |
