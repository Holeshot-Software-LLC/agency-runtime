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
candidate_commit: 9a940eb02d1eacdb2a8ad625cbc53c3bac4d35e1
evidence_cutoff: 2026-09-02
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/426
---

# AR-356 acceptance verification record

Fail-open capsule disclosure: builder evidence cited by the integrator against the merged
candidate `9a940eb0`; every verdict below comes from one isolated
single-check verifier run (`scripts/verify_acceptance.py`, codex transport)
that saw only that criterion and its own rows.

## Builder evidence

| Criterion | Kind | Artifact | Observed | Source |
|---|---|---|---|---|
| 1 | test | `test_fail_open_capsule_discloses_the_staffing_failure_on_every_host` | 2026-09-01 | `tests/test_fail_open_disclosure.py:159-191` |
| 1 | test | `test_workforce_inference_failure_discloses_its_staffing_codes_without_detail` | 2026-09-01 | `tests/test_fail_open_disclosure.py:218-261` |
| 1 | file | `_fail_open_preflight_result` | 2026-09-01 | `agency_runtime/core/preflight.py:919-1027` |
| 1 | file | `HOST_ADAPTERS` | 2026-09-01 | `tests/test_fail_open_disclosure.py:52-57` |
| 1 | file | `HookBridge._handle_user_prompt_submit` | 2026-09-01 | `agency_runtime/adapters/hooks.py:2528-2593` |
| 1 | file | `hermes bridge pre_llm_call_handler` | 2026-09-01 | `agency_runtime/adapters/hermes/bridge.py:555-570` |
| 1 | file | `openclaw node_bridge pre_llm_call_handler` | 2026-09-01 | `agency_runtime/adapters/openclaw/node_bridge.py:2025-2050` |
| 2 | test | `test_staffed_turns_never_carry_the_disclosure` | 2026-09-01 | `tests/test_fail_open_disclosure.py:264-285` |
| 2 | test | `test_resident_kernel_is_compact_versioned_and_content_addressed` | 2026-09-01 | `tests/test_resident_managers.py:76-108` |
| 2 | file | `RESIDENT_MANAGER_KERNEL / RESIDENT_MANAGER_KERNEL_HASH` | 2026-09-01 | `agency_runtime/core/resident_managers.py:10-42` |
| 2 | file | `kernel=v5:62c94d87 live receipt` | 2026-09-01 | `docs/roadmap/issue-AR-355-working-agreements-resident-manager.md:141` |
| 3 | test | `test_disclosure_wording_is_a_versioned_hash_pinned_contract` | 2026-09-01 | `tests/test_fail_open_disclosure.py:63-78` |
| 3 | test | `test_worst_case_disclosure_stays_inside_its_budget_on_one_line` | 2026-09-01 | `tests/test_fail_open_disclosure.py:81-88` |
| 3 | file | `FAIL_OPEN_DISCLOSURE_TEMPLATE / FAIL_OPEN_DISCLOSURE_HASH` | 2026-09-01 | `agency_runtime/core/fail_open_disclosure.py:30-45` |

## Verification

| Criterion | Verdict | Verifier run | Evidence digest | Observed | Reason |
|---|---|---|---|---|---|
| 1 | satisfied | `AR-356.1-20260902-9be4f543` | `081718cfccfb71efbb2f7c66fb982e3253e47ae0ed461cae296e962b7ed9634e` | 2026-09-02 | The cited parameterized test covers codex, claude, hermes, and openclaw and verifies one capsule disclosure containing the persisted bounded reason codes, while the inference test verifies staffing codes appear and provider detail does not. |
| 2 | absent | `AR-356.2-20260902-e2a37c7d` | `83f2c97ba976bb659368702d89c3140405d131249830b7e9da8ea38044151c32` | 2026-09-02 | The excerpts prove disclosure markers are absent and the kernel is internally content-addressed, but provide no prior staffed-capsule bytes or prior kernel hash demonstrating they are untouched and byte-identical. |
| 3 | satisfied | `AR-356.3-20260902-f07b868d` | `c4e2aba03c5514e00d515376b1319b7920fe9761284220e64308ace387eec5e9` | 2026-09-02 | The excerpts show the named regression tests pin version 1, both template hashes, recompute the disclosure hash, and enforce the 512-character single-line bound. |
