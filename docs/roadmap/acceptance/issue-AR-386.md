---
title: "AR-386 acceptance verification record"
status: active
category: roadmap
created: 2026-09-03
updated: 2026-09-03
tags: [acceptance, verification]
related:
  - docs/roadmap/issue-AR-386-strict-critic-vetoes-verifier-accepted-install-turns.md
  - docs/decisions/0200-bind-the-strict-critic-to-the-advisory-doctrine.md
supersedes: []
superseded_by: null
type: acceptance-verification
issue_id: AR-386
candidate_commit: 6b79736c0116331094630f7f252fa68992a1fb8d
evidence_cutoff: 2026-09-03
tracker_url: null
---

# AR-386 acceptance verification record

Pending draft. The strict critic's contract and system prompt state the
advisory doctrine, and a veto's codes reach the staffing decision in
projected form so both durable receipts and the fail-open disclosure name
it. Criteria 2 and 3 are evidenced live on the branch runtime under the
installed strict mode, with the critic served by the same deployment that
vetoed every install turn on the AR-384 measurement.

## Builder evidence

| Criterion | Kind | Artifact | Observed | Source |
|---|---|---|---|---|
| 1 | file | `_CRITIC_SYSTEM states that Agency is advisory and the host executes, that no worker can or need hold live authority, that a plan- or review-authority unit for host-side work is the intended shape, that roster_coverage_gap entries are roster facts, and that the critic must not demand an implementation unit the planner did not plan` | 2026-09-03 | `agency_runtime/core/workforce/inference.py:389-416` |
| 1 | file | `_CRITIC_VETO_GROUNDS and _CRITIC_NEVER_VETO_FOR name the grounds the critic may veto on and the grounds the doctrine rules out` | 2026-09-03 | `agency_runtime/core/workforce/inference.py:3448-3462` |
| 1 | file | `the critic_contract document carries workforce_is_advisory, execution_authority_holder host, selected_authority_bound_by_eligibility, roster_coverage_gaps_are_runtime_waivers, plan_authority_units_for_host_side_work_are_intended, veto_grounds and never_veto_for` | 2026-09-03 | `agency_runtime/core/workforce/inference.py:3524-3540` |
| 1 | test | `test_the_critic_contract_and_system_prompt_state_the_advisory_doctrine drives the strict flow, asserts every doctrine field and both lists on the contract the critic received, and every doctrine phrase in the system prompt` | 2026-09-03 | `tests/test_strict_critic_doctrine.py:258-290` |
| 1 | test | `test_the_captured_doctrine_breaking_codes_are_named_as_never_grounds asserts the two captured codes stand on grounds the contract rules out` | 2026-09-03 | `tests/test_strict_critic_doctrine.py:369-379` |
| 1 | command-output | `the critic_contract the live critic received on turn 209, with every doctrine field and both lists` | 2026-09-03 | `docs/roadmap/acceptance/evidence/AR-386-evidence-20260903.txt:40-47` |
| 2 | command-output | `turn 304, a helix wording first used today under AR-385 where the old critic vetoed it: the critic approved and the turn ended accepted with desktop-app-engineer, operations-manager, cross-platform-release-verifier and application-integration-verifier staffed, under the installed strict mode` | 2026-09-03 | `docs/roadmap/acceptance/evidence/AR-386-evidence-20260903.txt:9-31` |
| 2 | command-output | `turn 209, the helix wording the old critic vetoed on the AR-384 measurement: approved, accepted with six specialists staffed` | 2026-09-03 | `docs/roadmap/acceptance/evidence/AR-386-evidence-20260903.txt:9-31` |
| 2 | file | `_strict_critic sends the bound contract and returns no rejection code on approval, so the accepted decision stands` | 2026-09-03 | `agency_runtime/core/workforce/inference.py:3509-3618` |
| 2 | test | `test_an_approval_leaves_the_verified_decision_and_its_advisories_untouched` | 2026-09-03 | `tests/test_strict_critic_doctrine.py:293-301` |
| 3 | command-output | `the nine 2026-09-03 wordings re-run under the bound critic: four vetoes (204, 205, 208) and two approvals (209, 304 alongside) carry only wrong-neighbor-selection; neither selected-team-lacks-live-installation-authority nor missing-implementation-lifecycle-assurance recurred` | 2026-09-03 | `docs/roadmap/acceptance/evidence/AR-386-evidence-20260903.txt:9-31` |
| 3 | command-output | `each veto reached the durable preflight-failure receipt as staffing_critic_rejected plus critic_wrong_neighbor_selection, so the code is readable without the capture harness` | 2026-09-03 | `docs/roadmap/acceptance/evidence/AR-386-evidence-20260903.txt:33-38` |
| 3 | file | `_critic_rejected_staffing carries the critic's projected codes beside staffing_critic_rejected on the abstained decision` | 2026-09-03 | `agency_runtime/core/workforce/inference.py:3490-3506` |
| 3 | file | `_critic_receipt_codes validates each code against the critic charset and projects it as critic_<code> under the receipt bound` | 2026-09-03 | `agency_runtime/core/workforce/inference.py:3473-3487` |
| 3 | file | `the veto branch replaces the bare class-code decision with the projected one` | 2026-09-03 | `agency_runtime/core/workforce/inference.py:4030-4041` |
| 3 | test | `test_a_veto_reaches_both_receipts_and_the_disclosure_beside_the_verifier_codes asserts the projected codes on the staffing decision, on preflight_staffing_reason_codes, on the routing receipt's global_reason_codes, and in the fail-open disclosure line` | 2026-09-03 | `tests/test_strict_critic_doctrine.py:304-344` |
| 3 | test | `test_projected_codes_are_bounded_and_carry_no_prose` | 2026-09-03 | `tests/test_strict_critic_doctrine.py:347-366` |

## Verification

| Criterion | Verdict | Verifier run | Evidence digest | Observed | Reason |
|---|---|---|---|---|---|
| 1 | satisfied | `AR-386.1-20260903-c6a70036` | `ba5766527a5bece42f48c0807ec46696b57d2716af352c2f10453f52eefa9885` | 2026-09-03 | The cited inference.py excerpts explicitly state in both _CRITIC_SYSTEM and critic_contract that Agency is advisory, waived roster coverage gaps are runtime facts, and plan-authority units for host-side work are intended. |
| 2 | satisfied | `AR-386.2-20260903-e29d950c` | `6e6cf866a70ee53b72c7f5dde6e6411cda4fe723c68fa88b604e9e35c2fda4b0` | 2026-09-03 | The AR-386 evidence excerpt records turn 304 as fresh wording first used that day and ending ACCEPTED with four named specialists under strict mode. |
| 3 | satisfied | `AR-386.3-20260903-95476868` | `51df9e3b8bb283ef55397d8d170ed70b1dd92cc15a5785410838c9ca1850eeba` | 2026-09-03 | AR-386 evidence lines 9-31 show that the only strict-critic vetoes among wordings 201-209 were 204, 205, and 208, each carrying only wrong-neighbor-selection and no execution-authority code. |
