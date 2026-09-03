---
title: "AR-384 acceptance verification record"
status: active
category: roadmap
created: 2026-09-03
updated: 2026-09-03
tags: [acceptance, verification]
related:
  - docs/roadmap/issue-AR-384-staff-decisions-die-on-uncoverable-typed-requirements.md
  - docs/decisions/0198-waive-the-typed-requirements-the-roster-declares-but-cannot-serve.md
supersedes: []
superseded_by: null
type: acceptance-verification
issue_id: AR-384
candidate_commit: pending
evidence_cutoff: 2026-09-03
tracker_url: null
---

# AR-384 acceptance verification record

Pending draft. The verifier waives the typed requirements some contract
declares but none covers eligibly for the unit, records each as
`roster_coverage_gap`, and keeps every other token mandatory; the `operations`
capability also reads the `operations` domain. Criterion 2 is evidenced at the
verifier: the captured helix reply replays to an accepted decision selecting
`operations-manager`, and a fresh-wording live turn reaches the same verifier
decision before the strict critic vetoes the turn for reasons outside this
issue (filed as AR-386).

## Builder evidence

| Criterion | Kind | Artifact | Observed | Source |
|---|---|---|---|---|
| 1 | file | `_roster_coverage_gaps splits a unit's uncovered tokens into waived (declared, unserved) and unknown` | 2026-09-03 | `agency_runtime/core/workforce/staffing_verifier.py:525-556` |
| 1 | file | `_minimum_team_with_required proves sufficiency over the requirements minus the waived set` | 2026-09-03 | `agency_runtime/core/workforce/staffing_verifier.py:612-641` |
| 1 | file | `_selection records one roster_coverage_gap reason per waived token and passes the waiver to the team search` | 2026-09-03 | `agency_runtime/core/workforce/staffing_verifier.py:751-771` |
| 1 | file | `roster_coverage_gap is advisory, so it rides on an accepted decision` | 2026-09-03 | `agency_runtime/core/workforce/staffing_verifier.py:114-126` |
| 1 | file | `the routing receipt carries the waived tokens as coverage_gaps beside the unit reason codes` | 2026-09-03 | `agency_runtime/core/selector/receipt_projection.py:470-480` |
| 1 | test | `test_unserved_domain_is_waived_and_recorded_on_the_accepted_decision asserts the accepted decision, the selected team and the exact AbstentionReason` | 2026-09-03 | `tests/test_roster_coverage_gap.py:176-204` |
| 1 | test | `test_a_coverable_token_still_needs_its_complement asserts the conjunctive rule still pulls in and demands an eligible complement` | 2026-09-03 | `tests/test_roster_coverage_gap.py:237-281` |
| 1 | test | `test_routing_receipt_names_the_waived_token_and_drops_prose asserts the receipt names domain:desktop and drops prose` | 2026-09-03 | `tests/test_roster_coverage_gap.py:511-566` |
| 2 | command-output | `offline replay of the captured helix recruiter reply: nomination validation accepted, unit-install-operation selected operations-manager, verify_staffing accepted with roster_coverage_gap domain:desktop` | 2026-09-03 | `docs/roadmap/acceptance/evidence/AR-384-evidence-20260903.txt:18-25` |
| 2 | command-output | `the same replay with the waiver alone still failed on capability:operations, which is why the operations rule reads the operations domain` | 2026-09-03 | `docs/roadmap/acceptance/evidence/AR-384-evidence-20260903.txt:10-16` |
| 2 | command-output | `live turn 203, fresh helix wording: the verifier accepted unit-install-plan (desktop+operations, plan authority) with operations-manager selected and roster_coverage_gap domain:desktop; the strict critic then vetoed the turn` | 2026-09-03 | `docs/roadmap/acceptance/evidence/AR-384-evidence-20260903.txt:48-54` |
| 2 | command-output | `nine fresh live turns: the verifier accepted the install unit in four, and no turn was rejected by the verifier on a waived token` | 2026-09-03 | `docs/roadmap/acceptance/evidence/AR-384-evidence-20260903.txt:36-46` |
| 2 | file | `_operations_rule admits a contract whose declared domain is operations` | 2026-09-03 | `agency_runtime/core/workforce/staffing_verifier.py:234-240` |
| 2 | test | `test_operations_capability_reads_the_operations_domain` | 2026-09-03 | `tests/test_roster_coverage_gap.py:327-334` |
| 2 | test | `test_staff_decision_survives_an_unserved_requirement_end_to_end drives plan_and_staff_workforce with the captured shape and asserts operations-manager is staffed first time` | 2026-09-03 | `tests/test_roster_coverage_gap.py:438-509` |
| 3 | file | `_typed_shortlists derives uncovered_requirements and waived_requirements from the same helper the verifier waives with` | 2026-09-03 | `agency_runtime/core/workforce/inference.py:1576-1614` |
| 3 | file | `_validate_nomination_decisions computes the waived set from that helper before naming an axis or a repair target` | 2026-09-03 | `agency_runtime/core/workforce/inference.py:2606-2628` |
| 3 | file | `_uncoverable_requirement_axis never names a waived token` | 2026-09-03 | `agency_runtime/core/workforce/inference.py:2424-2453` |
| 3 | test | `test_typed_recall_shows_the_same_waived_tokens_the_verifier_waives` | 2026-09-03 | `tests/test_roster_coverage_gap.py:314-325` |
| 3 | test | `test_repair_contract_names_only_the_coverable_axis asserts the axis names the coverable domain and the waived token is listed separately` | 2026-09-03 | `tests/test_roster_coverage_gap.py:336-375` |
| 3 | command-output | `the only live domain-axis failures name domain:platform, which typed_recall listed as covered (uncovered_requirements empty)` | 2026-09-03 | `docs/roadmap/acceptance/evidence/AR-384-evidence-20260903.txt:56-61` |
| 3 | command-output | `turns 202, 205 and 207 in the live table: every staff_without_safe_team:domain names a coverable token` | 2026-09-03 | `docs/roadmap/acceptance/evidence/AR-384-evidence-20260903.txt:36-46` |

## Verification

| Criterion | Verdict | Verifier run | Evidence digest | Observed | Reason |
|---|---|---|---|---|---|
