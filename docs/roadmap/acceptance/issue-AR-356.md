---
title: "AR-356 acceptance verification record"
status: active
category: roadmap
created: 2026-09-02
updated: 2026-09-02
tags: [acceptance, verification]
related:
  - docs/roadmap/issue-AR-356-disclose-fail-open-staffing-in-capsule.md
supersedes: []
superseded_by: null
type: acceptance-verification
issue_id: AR-356
candidate_commit: 54755999a2e5150a4adbcbf68b7e15240680c603
evidence_cutoff: 2026-09-02
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/426
---

# AR-356 acceptance verification record

Fail-open capsule disclosure: builder evidence cited by the integrator
against candidate `54755999` (the implementation `9a940eb0` plus the
kernel-hash literal pin); every verdict below comes from one isolated
single-check verifier run (`scripts/verify_acceptance.py`, codex transport)
that saw only that criterion and its own rows.

## Builder evidence

| Criterion | Kind | Artifact | Observed | Source |
|---|---|---|---|---|
| 1 | test | `test_fail_open_capsule_discloses_the_staffing_failure_on_every_host` | 2026-09-02 | `tests/test_fail_open_disclosure.py:162-194` |
| 1 | test | `test_workforce_inference_failure_discloses_its_staffing_codes_without_detail` | 2026-09-02 | `tests/test_fail_open_disclosure.py:221-264` |
| 1 | file | `_fail_open_preflight_result` | 2026-09-02 | `agency_runtime/core/preflight.py:919-1027` |
| 1 | file | `HOST_ADAPTERS (codex, claude, hermes, openclaw)` | 2026-09-02 | `tests/test_fail_open_disclosure.py:55-60` |
| 1 | file | `HookBridge._handle_user_prompt_submit` | 2026-09-02 | `agency_runtime/adapters/hooks.py:2528-2593` |
| 2 | test | `test_staffed_turns_never_carry_the_disclosure` | 2026-09-02 | `tests/test_fail_open_disclosure.py:278-299` |
| 2 | test | `test_kernel_hash_literal_is_the_one_bound_before_the_disclosure_landed` | 2026-09-02 | `tests/test_fail_open_disclosure.py:267-275` |
| 2 | test | `test_resident_kernel_is_compact_versioned_and_content_addressed` | 2026-09-02 | `tests/test_resident_managers.py:76-108` |
| 2 | file | `RESIDENT_MANAGER_KERNEL / RESIDENT_MANAGER_KERNEL_HASH` | 2026-09-02 | `agency_runtime/core/resident_managers.py:10-42` |
| 2 | file | `_result_from_recipe (staffed capsule assembly, no disclosure path)` | 2026-09-02 | `agency_runtime/core/preflight_recipe.py:673-865` |
| 2 | file | `kernel=v5:62c94d87 live receipt recorded before AR-356` | 2026-09-02 | `docs/roadmap/issue-AR-355-working-agreements-resident-manager.md:141` |
| 3 | test | `test_disclosure_wording_is_a_versioned_hash_pinned_contract` | 2026-09-02 | `tests/test_fail_open_disclosure.py:66-81` |
| 3 | test | `test_worst_case_disclosure_stays_inside_its_budget_on_one_line` | 2026-09-02 | `tests/test_fail_open_disclosure.py:84-91` |
| 3 | file | `FAIL_OPEN_DISCLOSURE_TEMPLATE / FAIL_OPEN_DISCLOSURE_HASH / MAX chars` | 2026-09-02 | `agency_runtime/core/fail_open_disclosure.py:30-45` |

## Verification

| Criterion | Verdict | Verifier run | Evidence digest | Observed | Reason |
|---|---|---|---|---|---|
| 1 | satisfied | `AR-356.1-20260902-dd2791b1` | `8d31ba2091aa330b328623949736bb85b7a4e97dadc2af6fd0a15bf720eeab81` | 2026-09-02 | The parametrized four-adapter test asserts one capsule-ending disclosure containing persisted bounded reason codes, while the inference-failure test asserts staffing codes appear and provider detail does not. |
| 2 | satisfied | `AR-356.2-20260902-47e7a7f1` | `5241795e1278c8fcc2687a8dec64c773f63422ab1af1c9ce67778dabca4f7e7b` | 2026-09-02 | The cited staffed-turn test confirms both disclosure markers are absent and preflight_recipe.py has no disclosure import, while the kernel test recomputes its hash and pins it to the pre-change v5 hash recorded in AR-355. |
| 3 | satisfied | `AR-356.3-20260902-2816ce8d` | `b0d4cfe4a0612e1787c74398940021f45b43825a1004f97ac2c71cc1138c3e0b` | 2026-09-02 | The cited tests pin version 1, both expected template hashes, recompute the disclosure template hash, and enforce the 512-character single-line bound. |
