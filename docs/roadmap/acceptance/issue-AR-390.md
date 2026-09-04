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
candidate_commit: pending
evidence_cutoff: 2026-09-04
tracker_url: null
---

# AR-390 acceptance verification record

Pending draft. The compact recruiter card and the critic's neighbourhood card
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
| 4 | command-output | `offline replays of the two captured recruiter calls with every outcome on every card: the release verifier required three of three on turn 202 against two of three at baseline, one of three on turn 205 against none` | 2026-09-04 | `docs/roadmap/acceptance/evidence/AR-390-evidence-20260904.txt:23-30` |
| 4 | command-output | `live on the eleven wordings against the ADR-0205 run: the release verifier on the verification unit in 7 of 8 critic-reached turns against 5 of 9; completed 4 against 6 with three pre-critic losses and four vetoes on other units, recorded per turn` | 2026-09-04 | `docs/roadmap/acceptance/evidence/AR-390-evidence-20260904.txt:31-59` |
| 4 | command-output | `the cut as the recruiter saw it and the roster's outcome counts` | 2026-09-04 | `docs/roadmap/acceptance/evidence/AR-390-evidence-20260904.txt:7-22` |

## Verification

| Criterion | Verdict | Verifier run | Evidence digest | Observed | Reason |
|---|---|---|---|---|---|
