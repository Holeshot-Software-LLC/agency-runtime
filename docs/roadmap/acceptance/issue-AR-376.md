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
candidate_commit: 8447eb76092327d22d3e10fab57e4ecc3679c32b
evidence_cutoff: 2026-09-02
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/550
---

# AR-376 acceptance verification record

Builder evidence for the bounded hiring workforce projection, cited against
the AR-376 implementation commit `8447eb76`; every verdict below comes from
one isolated single-check verifier run (`scripts/verify_acceptance.py`, codex
transport) that saw only that criterion and its own builder rows.

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
| 1 | satisfied | `AR-376.1-20260902-45a220f7` | `a33d38f90bd718539ccae0fe8f279f25066f15e25d5a4b4c0779e41d9de587b3` | 2026-09-02 | The excerpts show a 12-field projection with a comment tying every field to duplicate detection or amend-overlap, applied to all contracts in roster order; tests verify disabled workers and both hiring prompts receive it. |
| 2 | satisfied | `AR-376.2-20260902-f79c86c6` | `3b86bc04d9949e3e5d808b33b0b5f30c8a8af0dc9aa548603eb28cd412ffd416` | 2026-09-02 | The cited evidence file records 291 workers, 115,745 to 44,067 prompt tokens, 441,982 to 208,654 bytes, a 2.63x reduction, and states both payloads used the same unit, gap, system prompt, and route. |
| 3 | satisfied | `AR-376.3-20260902-c32a1ffb` | `3859669726e18c91c67b6c739f0ea0ddeb14d198f47bf4c27af3ff90659a0316` | 2026-09-02 | The cited excerpts show four passing tests pinning the exact projection fields, duplicate-rule axes, dropped contract fields, all workers including disabled, and exclusion of incumbent revision identity from both prompts. |
