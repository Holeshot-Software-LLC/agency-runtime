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
  - docs/decisions/0201-constrain-the-planner-domains-to-what-the-roster-serves.md
supersedes: []
superseded_by: null
type: acceptance-verification
issue_id: AR-384
candidate_commit: 7c67b524bcbad9a00bcf269d6fbbe20c27810879
evidence_cutoff: 2026-09-03
tracker_url: null
---

# AR-384 acceptance verification record

Pending draft, re-opened from the record frozen at `1711bcaa`. That freeze
returned criteria 1 and 3 satisfied and criterion 2 contradicted on the
literal unit id `unit-install-operation`, which no fresh planner run
reproduces; criterion 2 has since been reworded to the unit shape and
criterion 4 added for option 2 (ADR-0201), so every verdict is re-run on the
next freeze. The verifier waives the typed requirements some contract
declares but none covers eligibly for the unit and records each as
`roster_coverage_gap` (ADR-0198); the planner is shown, per artifact kind,
the domains the roster serves under that kind's authority and a unit none of
whose domains is served is rejected for planner repair, while the
`platform-engineering` category no longer promotes the API platform card into
the `platform` domain (ADR-0201). Criterion 2 is evidenced at the verifier:
the captured helix reply replays to an accepted decision selecting
`operations-manager`, and fresh-wording live turns reach the same decision on
plan-authority install units carrying `operations`.

## Builder evidence

| Criterion | Kind | Artifact | Observed | Source |
|---|---|---|---|---|
| 1 | file | `_roster_coverage_gaps splits a unit's uncovered tokens into waived (declared, unserved) and unknown` | 2026-09-03 | `agency_runtime/core/workforce/staffing_verifier.py:525-556` |
| 1 | file | `_minimum_team_with_required proves sufficiency over the requirements minus the waived set` | 2026-09-03 | `agency_runtime/core/workforce/staffing_verifier.py:612-641` |
| 1 | file | `_selection records one roster_coverage_gap reason per waived token and passes the waiver to the team search` | 2026-09-03 | `agency_runtime/core/workforce/staffing_verifier.py:751-771` |
| 1 | file | `roster_coverage_gap is advisory, so it rides on an accepted decision` | 2026-09-03 | `agency_runtime/core/workforce/staffing_verifier.py:114-126` |
| 1 | file | `the routing receipt carries the waived tokens as coverage_gaps beside the unit reason codes` | 2026-09-03 | `agency_runtime/core/selector/receipt_projection.py:495-507` |
| 1 | test | `test_unserved_domain_is_waived_and_recorded_on_the_accepted_decision asserts the accepted decision, the selected team and the exact AbstentionReason` | 2026-09-03 | `tests/test_roster_coverage_gap.py:176-204` |
| 1 | test | `test_a_coverable_token_still_needs_its_complement asserts the conjunctive rule still pulls in and demands an eligible complement` | 2026-09-03 | `tests/test_roster_coverage_gap.py:237-281` |
| 1 | test | `test_routing_receipt_names_the_waived_token_and_drops_prose asserts the receipt names domain:desktop and drops prose` | 2026-09-03 | `tests/test_roster_coverage_gap.py:511-566` |
| 2 | command-output | `offline replay of the captured helix recruiter reply: nomination validation accepted, the plan-authority install unit (desktop and operations) selected operations-manager, verify_staffing accepted with roster_coverage_gap domain:desktop` | 2026-09-03 | `docs/roadmap/acceptance/evidence/AR-384-evidence-20260903.txt:18-25` |
| 2 | command-output | `the same replay with the waiver alone still failed on capability:operations, which is why the operations rule reads the operations domain` | 2026-09-03 | `docs/roadmap/acceptance/evidence/AR-384-evidence-20260903.txt:10-16` |
| 2 | command-output | `live turn 203, fresh helix wording: the verifier accepted the plan-authority install unit the planner named unit-install-plan (desktop and operations) with operations-manager selected and roster_coverage_gap domain:desktop` | 2026-09-03 | `docs/roadmap/acceptance/evidence/AR-384-evidence-20260903.txt:48-54` |
| 2 | command-output | `live turn 304 under the AR-386 runtime, fresh helix wording: the turn completed with operations-manager staffed on both plan-authority install units and the critic approved` | 2026-09-03 | `docs/roadmap/acceptance/evidence/AR-386-evidence-20260903.txt:11-25` |
| 2 | command-output | `live turns 205, 206 and 305 under the ADR-0201 runtime: operations-manager selected on every plan-authority install unit (domains operations) and the turns completed; no fresh planner run reproduced the captured unit id` | 2026-09-03 | `docs/roadmap/acceptance/evidence/AR-384-option2-evidence-20260903.txt:47-71` |
| 2 | file | `_operations_rule admits a contract whose declared domain is operations` | 2026-09-03 | `agency_runtime/core/workforce/staffing_verifier.py:234-240` |
| 2 | test | `test_operations_capability_reads_the_operations_domain` | 2026-09-03 | `tests/test_roster_coverage_gap.py:327-334` |
| 2 | test | `test_staff_decision_survives_an_unserved_requirement_end_to_end drives plan_and_staff_workforce with the captured shape and asserts operations-manager is staffed first time` | 2026-09-03 | `tests/test_roster_coverage_gap.py:438-509` |
| 3 | file | `_typed_shortlists derives uncovered_requirements and waived_requirements from the same helper the verifier waives with` | 2026-09-03 | `agency_runtime/core/workforce/inference.py:1682-1752` |
| 3 | file | `_validate_nomination_decisions computes the waived set from that helper before naming an axis or a repair target` | 2026-09-03 | `agency_runtime/core/workforce/inference.py:2713-2768` |
| 3 | file | `_uncoverable_requirement_axis never names a waived token` | 2026-09-03 | `agency_runtime/core/workforce/inference.py:2548-2576` |
| 3 | test | `test_typed_recall_shows_the_same_waived_tokens_the_verifier_waives` | 2026-09-03 | `tests/test_roster_coverage_gap.py:314-325` |
| 3 | test | `test_repair_contract_names_only_the_coverable_axis asserts the axis names the coverable domain and the waived token is listed separately` | 2026-09-03 | `tests/test_roster_coverage_gap.py:336-375` |
| 3 | command-output | `the only live domain-axis failures of the AR-384 run name domain:platform, which typed_recall listed as covered (uncovered_requirements empty)` | 2026-09-03 | `docs/roadmap/acceptance/evidence/AR-384-evidence-20260903.txt:56-61` |
| 3 | command-output | `the one live domain-axis failure of the ADR-0201 run (turn 201) names domain:software-engineering, a coverable token the recruiter left unranked among eligible planners` | 2026-09-03 | `docs/roadmap/acceptance/evidence/AR-384-option2-evidence-20260903.txt:47-71` |
| 4 | file | `served_domains_by_artifact_kind builds a probe unit per artifact kind and admits every domain of a worker the verifier's eligibility accepts on this host` | 2026-09-03 | `agency_runtime/core/workforce/intent.py:397-458` |
| 4 | file | `COMPACT_INTENT_SYSTEM states that every unit must name a domain from planning_taxonomy.domains_by_artifact_kind for its artifact_kind and that host_context.platform is not a domain` | 2026-09-03 | `agency_runtime/core/workforce/intent.py:329-337` |
| 4 | file | `_unserved_domain_violations emits plan_unit_domains_unserved for a unit none of whose domains is served, exempting an unproven kind, compiler-chosen domains and a declared novel domain` | 2026-09-03 | `agency_runtime/core/workforce/plan_policy.py:568-603` |
| 4 | file | `_CATEGORY_DOMAINS no longer promotes platform-engineering to platform, so the API platform card stops being the only plan-authority coverer of platform` | 2026-09-03 | `agency_runtime/core/workforce/contract.py:80-112` |
| 4 | test | `test_an_unserved_plan_is_repaired_by_the_planner_before_the_recruiter_sees_it drives plan_and_staff_workforce: the first plan is rejected with the code, the repair prompt carries the served view, and the corrected plan staffs operations-manager` | 2026-09-03 | `tests/test_planner_domain_service.py:494-564` |
| 4 | test | `test_a_unit_none_of_whose_domains_is_served_is_rejected asserts the code for desktop+platform and platform alone and its absence when operations is beside desktop` | 2026-09-03 | `tests/test_planner_domain_service.py:248-283` |
| 4 | command-output | `eleven live turns under strict mode: zero recruiter attempts failed staff_without_safe_team on domain:platform, api-platform-engineer was never ranked or selected, no first plan named platform or desktop on a plan-authority unit, three turns completed` | 2026-09-03 | `docs/roadmap/acceptance/evidence/AR-384-option2-evidence-20260903.txt:40-71` |
| 4 | command-output | `offline replay of the eleven captured plans: four rejected at the planner on exactly the plan unit naming only desktop and platform, the reconciled roster no longer serving platform under plan authority` | 2026-09-03 | `docs/roadmap/acceptance/evidence/AR-384-option2-evidence-20260903.txt:15-38` |

## Verification

| Criterion | Verdict | Verifier run | Evidence digest | Observed | Reason |
|---|---|---|---|---|---|
| 1 | satisfied | `AR-384.1-20260903-68c6c116` | `705db49aa2cfccca66536ccc5f66770fcda03900a3b008b10cff629afce88056` | 2026-09-03 | The staffing verifier waives only declared-but-ineligible tokens, still requires all eligible-coverable requirements, accepts the tested sufficient team, and receipt projection exposes the waived token in coverage_gaps. |
| 2 | satisfied | `AR-384.2-20260903-42531a9c` | `9ea5911a637bef67c410823abeb79ec1071446e88086796957f62508a44bf47b` | 2026-09-03 | AR-384 evidence lines 18-25 show the captured reply accepted with operations-manager, while lines 48-54 show fresh turn 203 staffing operations-manager on an artifact=plan unit with desktop and operations domains and verifier status accepted. |
| 3 | satisfied | `AR-384.3-20260903-61d83a9d` | `629628ac5735193a85d72ea883310d129905fa41d0b5267b9fb4aaa026f6680b` | 2026-09-03 | The shared coverage-gap helper marks domain:desktop uncovered and waived, validation excludes waived tokens from failure-axis and repair targeting, and the test shows the remaining domain failure is for domain:quality-assurance instead. |
| 4 | satisfied | `AR-384.4-20260903-ccdd16e3` | `28fb4b569b9bbb3487a7bbf415f116813a9142a46ce83697daf285372d766fe4` | 2026-09-03 | The cited implementation and tests show per-artifact served-domain prompting, plan_unit_domains_unserved rejection, and planner repair before recruiting; the eleven-turn strict-mode artifact records zero domain:platform recruiter failures and zero api-platform-engineer rankings or selections. |
