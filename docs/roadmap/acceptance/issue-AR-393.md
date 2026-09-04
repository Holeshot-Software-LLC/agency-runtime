---
title: "AR-393 acceptance verification record"
status: active
category: roadmap
created: 2026-09-04
updated: 2026-09-04
tags: [acceptance, verification]
related:
  - docs/roadmap/issue-AR-393-declared-gaps-leave-no-hiring-account.md
  - docs/decisions/0210-account-for-every-declared-gap.md
supersedes: []
superseded_by: null
type: acceptance-verification
issue_id: AR-393
candidate_commit: d7106be13435a4243d9842e01bc7840d9909e696
evidence_cutoff: 2026-09-04
tracker_url: null
---

# AR-393 acceptance verification record

Builder evidence at `d7106be1` for criteria 1 to 4. Criterion 5 is a live
measurement and is **not** evidenced here: it requires preflight receipts
written by a host running this code, and the installed runtime is venv
`04adb230`. See "Not established here".

The three functions are pure over a duck-typed outcome, so criteria 1 to 4 are
driven with no provider and no credential, through the real
`_complete_gap_hiring_events` and `preflight_hiring_reason_codes` rather than a
stand-in.

## Builder evidence

| Criterion | Kind | Artifact | Observed | Source |
|---|---|---|---|---|
| 1 | file | `_all_gap_units returns every unit the staffing decision declared, including one whose id matches no plan unit, instead of intersecting the verifier's ids with the plan's` | 2026-09-04 | `agency_runtime/core/selector/pipeline.py:1546-1560` |
| 1 | file | `a unit the plan does not contain carries GAP_UNIT_ABSENT_FROM_PLAN, which names that condition` | 2026-09-04 | `agency_runtime/core/selector/pipeline.py:1478-1482` |
| 1 | test | `test_a_gap_unit_the_plan_does_not_contain_still_gets_an_event and test_an_absent_plan_is_the_same_case_as_an_empty_one` | 2026-09-04 | `tests/test_declared_gap_hiring_account.py:105-127` |
| 1 | command-output | `shape 1 through the real projection: main produces no gap unit, no event and an empty hiring_reason_codes; the branch produces the unit, one event and gap_unit_absent_from_plan on the receipt` | 2026-09-04 | `docs/roadmap/acceptance/evidence/AR-393-evidence-20260904.txt:14-18` |
| 2 | file | `_gap_hiring_verdicts computes one per-unit verdict naming the test that disqualified the unit; the survivors are exactly the units with an empty verdict, so the two answers cannot drift` | 2026-09-04 | `agency_runtime/core/selector/pipeline.py:1434-1516` |
| 2 | file | `a global code outside the hireable set puts GAP_GLOBAL_ABSTENTION and that code on every unit it disqualified` | 2026-09-04 | `agency_runtime/core/selector/pipeline.py:1502-1504` |
| 2 | file | `the event builder reads the verdict and appends the unit's own codes only when those codes are what disqualified it` | 2026-09-04 | `agency_runtime/core/selector/pipeline.py:1583-1605` |
| 2 | test | `test_a_global_code_travels_onto_every_event_it_disqualified and test_a_unit_inference_never_declared_names_that_and_not_its_own_codes` | 2026-09-04 | `tests/test_declared_gap_hiring_account.py:133-176` |
| 2 | test | `test_the_survivors_are_exactly_the_units_with_no_disqualifier pins the verdict map against both callers` | 2026-09-04 | `tests/test_declared_gap_hiring_account.py:243-264` |
| 2 | command-output | `shape 3 through the real projection: main lists no_safe_sufficient_team and recruiter_abstained on both events, neither of which disqualifies anything; the branch lists gap_global_abstention_code and selection_confidence_too_low` | 2026-09-04 | `docs/roadmap/acceptance/evidence/AR-393-evidence-20260904.txt:26-30` |
| 3 | file | `GAP_EVIDENCE_NOT_HIREABLE is written only when the unit's own codes include one outside _HIREABLE_GAP_CODES` | 2026-09-04 | `agency_runtime/core/selector/pipeline.py:1508-1516` |
| 3 | file | `the final branch, reached with the unit still hireable and no limit met, carries GAP_HIRE_NOT_ATTEMPTED instead of a code contradicting the tuple it was computed from` | 2026-09-04 | `agency_runtime/core/selector/pipeline.py:1606-1612` |
| 3 | test | `test_gap_evidence_not_hireable_appears_only_with_a_code_outside_the_set and test_a_still_hireable_unit_is_not_told_its_evidence_disqualified_it` | 2026-09-04 | `tests/test_declared_gap_hiring_account.py:194-232` |
| 4 | test | `test_no_event_lists_only_codes_that_support_the_opposite_conclusion asserts over all four reproduced shapes that every event has codes and that at least one is outside the hireable set` | 2026-09-04 | `tests/test_declared_gap_hiring_account.py:211-236` |
| 4 | command-output | `all three shapes from the issue's table, before and after, through the real receipt projection` | 2026-09-04 | `docs/roadmap/acceptance/evidence/AR-393-evidence-20260904.txt:13-49` |
| 5 | command-output | `the before-baseline this issue was filed on, re-measured read-only against the live store: 99 declaring receipts, 42 with empty hiring_reason_codes, window 2026-08-29 to 2026-09-03` | 2026-09-04 | `docs/roadmap/acceptance/evidence/AR-393-evidence-20260904.txt:6-10` |

## Verification

| Criterion | Verdict | Verifier run | Evidence digest | Observed | Reason |
|---|---|---|---|---|---|
| 1 | satisfied | `AR-393.1-20260904-3208aef8` | `e7a52ab6d3ff31dc23d815c9d84b1cf0a30e3f15956b040de194a83fcbf35a93` | 2026-09-04 | In the snapshot, pipeline.py:1472-1476 keeps declared gap ids outside the plan and assigns GAP_UNIT_ABSENT_FROM_PLAN (1417), _all_gap_units (1563) returns them, _complete_gap_hiring_events (1614) emits an event per unit, and routing["hiring_events"] is set (2011-2019); tests 102-119 pin this. |
| 2 | satisfied | `AR-393.2-20260904-b4ae13da` | `dedd16fe56fe9508219ae39fa22e88ac05003c0c51a49d6c8f220c62b8cad72a` | 2026-09-04 | pipeline.py:1471-1491 gives each disqualified unit a verdict naming the failed test and appends the global code; 1596-1604 puts it on the event; test_declared_gap_hiring_account.py:146-167 and evidence lines 45-49 show gap_global_abstention_code with selection_confidence_too_low on both events. |
| 3 | satisfied | `AR-393.3-20260904-242559cf` | `050328ad2fe0badb99d16c57d9b4fb0791468f62c5f23d74ab11108079195ff6` | 2026-09-04 | pipeline.py:1489-1490 is the only producer of GAP_EVIDENCE_NOT_HIREABLE (repo-wide grep) and emits it only when unit_codes - _HIREABLE_GAP_CODES is non-empty; lines 1600-1604 carry those codes onto the event, and tests at test_declared_gap_hiring_account.py:184-225 assert it. |
| 4 | satisfied | `AR-393.4-20260904-33a2a442` | `acc6f8790b924af19e90985eff23112318761feb83db5ca4e7bd9418e2416198` | 2026-09-04 | Evidence file lines 13-49 replay the three shapes through the real receipt projection: each declared gap yields an event whose codes include one outside the hireable set; pipeline.py:1433-1615 and the test at tests/test_declared_gap_hiring_account.py:201-225 confirm the rule. |
| 5 | contradicted | `AR-393.5-20260904-a59316f2` | `828000fef0f81a83707976c5ddea0b6f69494caf6a18e20aa66cd7834f275d4f` | 2026-09-04 | The only live measurement, AR-393-evidence-20260904.txt:6-10, re-measured read-only against the live store, reports 42 receipts declaring no_safe_sufficient_team with EMPTY hiring_reason_codes, not zero; the file states no credential was used, and sections 2-3 are simulated shapes and unit tests. |

## Builder notes

New tests 10, all passing. The affected selection on this branch is 2044
passed, 18 failed; every one of the 18 fails identically on `main` at
`82a85f48` and none is touched by this change.

The measurement in the issue is reproduced exactly: 99 receipts declaring
`no_safe_sufficient_team`, 42 of them silent, over the same window.

## Not established here

**Criterion 5 is not met.** It asks for the count of receipts declaring
`no_safe_sufficient_team` with empty `hiring_reason_codes` to be zero, measured
live. Preflight receipts are written by a host running the installed runtime,
which is venv `04adb230`; `agency route` is read-only and writes none, so no
run from this branch can produce one. The criterion needs this code installed
and a staffed turn, and should then be read over receipts recorded after that
install, with the 42 kept as the before-baseline: a code change cannot rewrite
stored rows.

**Which of the three conditions produced the live 42 is still not established.**
The leading candidate remains a repair re-planning the turn while the retained
staffing decision references the first plan's unit ids. That is now
`gap_unit_absent_from_plan` and will name itself on the first receipt that hits
it, which is what makes the condition answerable at all.
