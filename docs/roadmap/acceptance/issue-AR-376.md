---
title: "AR-376 acceptance verification record"
status: active
category: roadmap
created: 2026-09-02
updated: 2026-09-02
tags: [acceptance, verification]
related:
  - docs/roadmap/issue-AR-376-hiring-sends-the-entire-workforce.md
supersedes: []
superseded_by: null
type: acceptance-verification
issue_id: AR-376
candidate_commit: pending
evidence_cutoff: 2026-09-02
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/550
---

# AR-376 acceptance verification record

Pending draft. Builder evidence for the bounded hiring workforce projection,
cited against the working tree; the record freezes to the implementation
commit once that commit is an ancestor of `HEAD`, and verification rows are
written only then.

## Builder evidence

| Criterion | Kind | Artifact | Observed | Source |
|---|---|---|---|---|
| 1 | file | `HIRING_WORKFORCE_PROJECTION_FIELDS with the rule each of the twelve axes answers to` | 2026-09-02 | `agency_runtime/core/workforce/hiring.py:857-894` |
| 1 | file | `hiring_workforce_projection carries every contract in roster order` | 2026-09-02 | `agency_runtime/core/workforce/hiring.py:897-910` |
| 1 | file | `hire_contractor_for_gap builds complete_workforce from the projection` | 2026-09-02 | `agency_runtime/core/workforce/hiring.py:2208` |
| 1 | file | `_HIRE_SYSTEM says every worker appears, disabled included, as a bounded row` | 2026-09-02 | `agency_runtime/core/workforce/hiring.py:60-65` |
| 1 | test | `test_hiring_projection_carries_every_worker_including_disabled` | 2026-09-02 | `tests/test_workforce_dynamic_hiring.py:2948-2956` |
| 1 | test | `test_hiring_prompt_sends_the_projection_and_not_the_full_contract` | 2026-09-02 | `tests/test_workforce_dynamic_hiring.py:2959-2993` |
| 2 | command-output | `115,745 prompt_tokens before and 44,067 after, 441,982 to 208,654 bytes, same 291 workers` | 2026-09-02 | `docs/roadmap/acceptance/evidence/AR-376-evidence-20260902.txt:1-11` |
| 2 | file | `the before and after figures recorded on the issue` | 2026-09-02 | `docs/roadmap/issue-AR-376-hiring-sends-the-entire-workforce.md#acceptance` |
| 3 | test | `test_hiring_projection_is_pinned_to_the_axes_its_own_rules_read` | 2026-09-02 | `tests/test_workforce_dynamic_hiring.py:2920-2945` |
| 3 | test | `test_hiring_projection_carries_every_worker_including_disabled` | 2026-09-02 | `tests/test_workforce_dynamic_hiring.py:2948-2956` |
| 3 | test | `test_hiring_prompt_sends_the_projection_and_not_the_full_contract` | 2026-09-02 | `tests/test_workforce_dynamic_hiring.py:2959-2993` |
| 3 | test | `test_hiring_projection_is_smaller_than_the_full_contract` | 2026-09-02 | `tests/test_workforce_dynamic_hiring.py:2996-3003` |
| 3 | command-output | `the four projection cases PASSED under -W error` | 2026-09-02 | `docs/roadmap/acceptance/evidence/AR-376-evidence-20260902.txt:22-29` |

## Verification

| Criterion | Verdict | Verifier run | Evidence digest | Observed | Reason |
|---|---|---|---|---|---|
