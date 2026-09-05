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
candidate_commit: 18c04e21585698756d76787abdad3b2e29ff8479
evidence_cutoff: 2026-09-04
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/650
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
| 5 | command-output | `the after-install window, read with the credential sourced against a fresh copy of the live store: zero declaring receipts since the fix landed at 2026-09-04T16:01Z and zero since the last one at 2026-09-03T18:42:33Z; the 150 receipts since all end at routing, 131 as inference_unavailable, so no recruiter proposal was accepted and the declaring path never ran` | 2026-09-04 | `docs/roadmap/acceptance/evidence/AR-393-evidence-20260904.txt:54-81` |

## Verification

| Criterion | Verdict | Verifier run | Evidence digest | Observed | Reason |
|---|---|---|---|---|---|
| 1 | satisfied | `AR-393.1-20260904-f3219542` | `2f592531bb004668bb3436822f9a2789ba4983f5707e859fb7f882e69caff3f6` | 2026-09-04 | In the snapshot, _gap_hiring_verdicts (pipeline.py:1499-1517) keeps gap ids outside the plan and labels them GAP_UNIT_ABSENT_FROM_PLAN, _all_gap_units returns all of them (1708-1720), and _complete_gap_hiring_events emits one event per id (1735-1772); tests at line 102-119 assert this. |
| 2 | satisfied | `AR-393.2-20260904-240a5d35` | `628f0a15857eb50a7869cf81613ea1a2d84692c3cb9e98b72ce7a45fbc9d8931` | 2026-09-04 | Snapshot pipeline.py:1512-1531 gives every non-hireable unit a verdict naming the failed test, emitted onto the event at 1742-1761; the global case yields (gap_global_abstention_code, *global codes) at 1519-1520, pinned by tests at test_declared_gap_hiring_account.py:145-167 and evidence line 48. |
| 3 | satisfied | `AR-393.3-20260904-e9e76fe0` | `b578f78c8725b266d2a09e017070e770f39c8dbee8a5385cb93518719eabe081` | 2026-09-04 | pipeline.py:1530-1531 is the only producer and writes GAP_EVIDENCE_NOT_HIREABLE only when own = unit_codes - _HIREABLE_GAP_CODES is non-empty; lines 1753-1761 emit those codes on the event, grep shows no other producer, and tests at test_declared_gap_hiring_account.py:184-225 pin the rule. |
| 4 | satisfied | `AR-393.4-20260904-831e319e` | `ebcb71777b286b7bd6c0f9c9f028d64b5d3f9975df24d749db33e27e7315877d` | 2026-09-04 | tests/test_declared_gap_hiring_account.py:201-225 asserts the invariant over all three table shapes; pipeline.py:1708-1772 emits one event per declared gap unit with verdict codes outside _HIREABLE_GAP_CODES (:1436-1447); evidence file lines 32-49 shows matching branch output. |
| 5 | contradicted | `AR-393.5-20260904-8b96b11f` | `9456a7d8b04788dbb1100ac8598602479de76d1c0b37a3315d3ac8e8e72790d0` | 2026-09-04 | AR-393-evidence-20260904.txt:59-63 shows the live store still holds 42 declaring receipts with empty hiring_reason_codes; the reported 0 is over an empty after-fix window (no declaring receipts since 2026-09-03), and issue-AR-393.md:88-92 says the condition behind the 42 is unnamed. |

## Builder notes

New tests 10, all passing. The affected selection on this branch is 2044
passed, 18 failed; every one of the 18 fails identically on `main` at
`82a85f48` and none is touched by this change.

The measurement in the issue is reproduced exactly: 99 receipts declaring
`no_safe_sufficient_team`, 42 of them silent, over the same window.

## Not established here

**Criterion 5 is not measurable yet, and the reason is now recorded.** The
after-install window was read on 2026-09-04 with the credential sourced
(evidence section 5): zero declaring receipts since the fix, because no
recruiter proposal has been accepted since 2026-09-03T18:42:33Z and the
declaring path runs after one. The count the criterion asks for is zero over
an empty set, which proves nothing; the 42 are pre-fix rows a code change
cannot rewrite. It becomes measurable on the first staffed turn that declares
a gap, which is gated on AR-394's recruiter and AR-370's retrieval.

**As originally written:** it asks for the count of receipts declaring
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
