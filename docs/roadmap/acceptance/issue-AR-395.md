---
title: "AR-395 acceptance verification record"
status: active
category: roadmap
created: 2026-09-04
updated: 2026-09-04
tags: [acceptance, verification]
related:
  - docs/roadmap/issue-AR-395-preflight-stage-vocabulary-is-incomplete.md
  - agency_runtime/core/preflight_failure.py
  - agency_runtime/core/reply_budget.py
  - tests/test_preflight_stage_vocabulary.py
supersedes: []
superseded_by: null
type: acceptance-verification
issue_id: AR-395
candidate_commit: pending
evidence_cutoff: 2026-09-04
tracker_url: null
---

# AR-395 acceptance verification record

`PREFLIGHT_PROVIDER_STAGES` now holds every label the runtime passes to a
stage invoker, and a test pins the set against the labels found in the source
so a stage added later fails the suite instead of degrading into `"unknown"`.

The issue named three missing labels. The source scan the test performs found
**six**: the three named (`subject`, `security_review`, `safety_repair`) and
three more in the same condition — `hiring-critic`, `hiring-repair` and
`hiring-repair-critic`, all passed to `hiring.py`'s `_invoke`. AR-385's
`STAGE_REPLY_BUDGET_TOKENS` already enumerates all six, which is the
independent corroboration: the transport knew about these stages and the
receipt's vocabulary did not.

No validation codes were lost by the six. `_validation_reason_codes`
(`inference.py:1547-1562`) returns `()` for every one of them, and
`HiringInferenceAttempt` (`hiring.py:556-567`) has no
`validation_reason_codes` field at all, so the drop
`_project_validation_reason_codes` performs for an unrecognised stage was
inert here. What was lost is only the stage's name, which is what the issue
measured.

## Builder evidence

| Criterion | Kind | Artifact | Observed | Source |
|---|---|---|---|---|
| 1 | file | `PREFLIGHT_PROVIDER_STAGES holds subject, security_review, safety_repair, hiring-critic, hiring-repair and hiring-repair-critic beside the nine it already held` | 2026-09-04 | `agency_runtime/core/preflight_failure.py:123-141` |
| 1 | file | `the six labels are the ones inference.py and hiring.py pass to a stage invoker: subject at inference.py:4402, security_review at hiring.py:1344, safety_repair at hiring.py:1461, hiring-repair at hiring.py:1188, hiring-repair-critic at hiring.py:1228, hiring-critic at hiring.py:2408` | 2026-09-04 | `agency_runtime/core/workforce/hiring.py:1188` |
| 1 | file | `STAGE_REPLY_BUDGET_TOKENS names the same eleven stages from the transport side, so the two tables now agree` | 2026-09-04 | `agency_runtime/core/reply_budget.py:42-56` |
| 2 | test | `test_the_receipt_vocabulary_equals_the_stages_the_runtime_runs asserts set equality between the labels parsed out of inference.py and hiring.py, plus three named non-invocation members, and PREFLIGHT_PROVIDER_STAGES` | 2026-09-04 | `tests/test_preflight_stage_vocabulary.py:92-95` |
| 2 | test | `_stage_labels walks the module AST for every string literal passed as a stage= keyword, so a label is found wherever it is written rather than where a regex expects it; this is what found the three hyphenated hiring stages the issue did not name` | 2026-09-04 | `tests/test_preflight_stage_vocabulary.py:61-73` |
| 2 | test | `test_the_source_scan_finds_the_stage_labels_it_is_meant_to_find guards the scan, so the equality above cannot pass vacuously if the AST walk breaks` | 2026-09-04 | `tests/test_preflight_stage_vocabulary.py:84-89` |
| 2 | test | `test_every_stage_the_transport_budgets_can_name_itself_on_a_receipt asserts STAGE_REPLY_BUDGET_TOKENS is a subset of both the receipt vocabulary and the source labels, a second independent source of the same truth` | 2026-09-04 | `tests/test_preflight_stage_vocabulary.py:98-110` |
| 3 | test | `test_a_stage_the_runtime_runs_names_itself_on_the_receipt drives project_preflight_provider_attempts with an attempt from each of the six stages and asserts the projected entry keeps that stage name` | 2026-09-04 | `tests/test_preflight_stage_vocabulary.py:113-133` |
| 4 | file | `the rewrite to "unknown" is unchanged: a stage outside the set is still replaced` | 2026-09-04 | `agency_runtime/core/preflight_failure.py:268-270` |
| 4 | test | `test_unknown_still_means_a_stage_the_projection_could_not_read projects an undeclared stage and asserts the entry reads "unknown", and that "unknown" is still a member` | 2026-09-04 | `tests/test_preflight_stage_vocabulary.py:136-152` |
| 2 | command-output | `10 new tests pass on the branch; the same 10 against unfixed main give 8 failed, 2 passed, so the suite pins the change` | 2026-09-04 | `docs/roadmap/acceptance/evidence/AR-395-evidence-20260904.txt:3-19` |
| 1 | command-output | `the affected preflight surface is 302 passed, 1 skipped; the four heavier files are 1 failed, 332 passed on the branch and identically 1 failed, 332 passed on clean main` | 2026-09-04 | `docs/roadmap/acceptance/evidence/AR-395-evidence-20260904.txt:20-30` |

## Verification

| Criterion | Verdict | Verifier run | Evidence digest | Observed | Reason |
|---|---|---|---|---|---|

## Builder notes

`combined` and `selector` stay in the set and are named in the test as
non-invocation members. `combined` is the evals' provider-configuration stage
and the planner's partner in `_project_validation_reason_codes:208`;
`selector` has no producer today and is retained so an older receipt still
projects. Naming them is what makes the equality a real constraint: a label
added to the runtime cannot be absorbed by an unexplained remainder.

`recall_embedding` is the one asymmetry between the two tables. An embedding
call returns vectors and takes the fallback reply budget, so it is budgeted
without being listed in `STAGE_REPLY_BUDGET_TOKENS`; the test asserts the
subset direction that holds and says why.

The one failing test in the heavier surface,
`test_dashboard_workforce_and_hiring_apis_share_revision_bound_lifecycle`,
fails identically on clean `main` — a leading-capital `Changed artifacts`
string in a live-derived contract — and is untouched by this change.
