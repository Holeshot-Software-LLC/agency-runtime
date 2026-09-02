---
title: "AR-355 acceptance verification record"
status: active
category: roadmap
created: 2026-09-02
updated: 2026-09-02
tags: [acceptance, verification]
related:
  - docs/roadmap/issue-AR-355-working-agreements-resident-manager.md
supersedes: []
superseded_by: null
type: acceptance-verification
issue_id: AR-355
candidate_commit: 62e43b57461aa06d2339a31fb0c252b1c5fef527
evidence_cutoff: 2026-09-02
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/422
---

# AR-355 acceptance verification record

Working agreements as a resident manager: builder evidence cited by the
integrator against candidate `62e43b57` (the implementation plus the
per-host policy proof); every verdict below comes from one isolated
single-check verifier run (`scripts/verify_acceptance.py`, codex transport)
that saw only that criterion and its own rows.

## Builder evidence

| Criterion | Kind | Artifact | Observed | Source |
|---|---|---|---|---|
| 1 | test | `test_policy_reaches_staffed_and_unstaffed_turns_on_every_host (codex, claude, hermes, openclaw)` | 2026-09-02 | `tests/test_operator_policy.py:188-228` |
| 1 | test | `test_configured_policy_reaches_the_turn_after_agencys_own_frame` | 2026-09-02 | `tests/test_operator_policy.py:177-185` |
| 1 | test | `test_every_configuration_path_accepts_operator_policy_identically` | 2026-09-02 | `tests/test_operator_policy.py:127-148` |
| 1 | file | `render_operator_policy` | 2026-09-02 | `agency_runtime/core/operator_policy.py:144-155` |
| 1 | file | `AR-355 implementation record (live verification 2026-09-01)` | 2026-09-02 | `docs/roadmap/issue-AR-355-working-agreements-resident-manager.md#implementation-2026-09-01` |
| 2 | test | `test_resident_kernel_is_compact_versioned_and_content_addressed (roster line present, anti-self-staffing pinned)` | 2026-09-02 | `tests/test_resident_managers.py:76-108` |
| 2 | test | `test_kernel_hash_literal_is_the_one_bound_before_the_disclosure_landed (62c94d87...)` | 2026-09-02 | `tests/test_fail_open_disclosure.py:267-275` |
| 2 | file | `RESIDENT_MANAGER_KERNEL v5 text and hash` | 2026-09-02 | `agency_runtime/core/resident_managers.py:10-42` |
| 2 | file | `live receipt: rebound to rmb-ab4a5952 with kernel=v5:62c94d87, delivery=injected` | 2026-09-02 | `docs/roadmap/issue-AR-355-working-agreements-resident-manager.md:138-146` |
| 2 | file | `ledger row d2222f37 recording the live v5 binding` | 2026-09-02 | `docs/worklog/README.md:1567` |
| 3 | file | `deploy and battery record (projection eed132308c55, four batteries green)` | 2026-09-02 | `docs/roadmap/issue-AR-355-working-agreements-resident-manager.md:91-130` |
| 3 | file | `resident_manager_turn_reference_context (binding line reports manager + kernel hash)` | 2026-09-02 | `agency_runtime/core/resident_manager_binding.py:496-532` |
| 3 | tracker | `PR #425 kernel v5 implementation` | 2026-09-02 | `https://github.com/Holeshot-Software-LLC/agency-runtime/pull/425` |
| 3 | receipt | `harness battery receipt 20260901T212108811748Z-claude` | 2026-09-02 | `20260901T212108811748Z-claude` |
| 4 | test | `test_report_isolates_the_ar355_delta_and_the_fail_open_shape` | 2026-09-02 | `tests/test_context_budget.py:72-110` |
| 4 | test | `test_staffed_capsules_are_replayed_from_a_real_ready_turn` | 2026-09-02 | `tests/test_context_budget.py:132-200` |
| 4 | test | `test_cli_prints_the_budget_and_json` | 2026-09-02 | `tests/test_context_budget.py:203-225` |
| 4 | file | `context_budget_report` | 2026-09-02 | `agency_runtime/core/context_budget.py:392-589` |
| 4 | file | `measured numbers recorded in the acceptance box` | 2026-09-02 | `docs/roadmap/issue-AR-355-working-agreements-resident-manager.md#acceptance` |

## Verification

| Criterion | Verdict | Verifier run | Evidence digest | Observed | Reason |
|---|---|---|---|---|---|
| 1 | satisfied | `AR-355.1-20260902-c0c4cf1e` | `cadb1250c9a8a5a64f59dd596b3e62ec65de1f7db9a28e7608e16e6457bc85c7` | 2026-09-02 | The cited tests cover staffed and fail-open turns on codex, claude, hermes, and openclaw, verify policy placement beside the steward, and show operator_policy survives owner configuration paths without deployment. |
| 2 | satisfied | `AR-355.2-20260902-6b21e0d6` | `4e7e2e39a2566e445e57ecf7a4b02d1220812873aedecede0c2af95574828539` | 2026-09-02 | The v5 kernel excerpt places the roster-awareness line between delegation-neutrality and unchanged anti-self-staffing text, while the pinned 62c94d87 hash and documented rmb-ab4a5952 injected receipt corroborate the live observation. |
| 3 | satisfied | `AR-355.3-20260902-1e5cbe56` | `4cf5a0f1c9c3d85c6f1b6c2d0281d33394e52468618b4c633e05bf538a2b5834` | 2026-09-02 | The roadmap excerpt records the v4→v5 change, four-host re-wire, and four green batteries, while the binding excerpt emits both kernel hash and manager slugs and the implementation identifies operator_policy as separately hashed. |
| 4 | satisfied | `AR-355.4-20260902-d5560304` | `82708fe799e7906ad516a9f489512edd0259547827765a08118e8b353b2a4b9a` | 2026-09-02 | The acceptance excerpt records all stated measurements, while context_budget_report and the cited tests demonstrate component sizing, AR-355 delta calculation, fail-open totals, staffed-capsule replay, and CLI output. |
