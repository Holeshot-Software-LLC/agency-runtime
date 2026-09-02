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
candidate_commit: 63f7e60f803ff3cfe22fb4ed998656b32c2c9beb
evidence_cutoff: 2026-09-02
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/422
---

# AR-355 acceptance verification record

Working agreements as a resident manager: builder evidence cited by the integrator against the merged
candidate `63f7e60f`; every verdict below comes from one isolated
single-check verifier run (`scripts/verify_acceptance.py`, codex transport)
that saw only that criterion and its own rows.

## Builder evidence

| Criterion | Kind | Artifact | Observed | Source |
|---|---|---|---|---|
| 1 | test | `test_configured_policy_reaches_the_turn_after_agencys_own_frame` | 2026-09-02 | `tests/test_operator_policy.py:177-185` |
| 1 | test | `test_fail_open_capsule_keeps_the_operator_policy_after_agencys_frame` | 2026-09-02 | `tests/test_fail_open_disclosure.py:197-218` |
| 1 | test | `test_every_configuration_path_accepts_operator_policy_identically` | 2026-09-02 | `tests/test_operator_policy.py:127-148` |
| 1 | file | `render_operator_policy` | 2026-09-02 | `agency_runtime/core/operator_policy.py:144-155` |
| 1 | file | `AR-355 implementation record (live verification 2026-09-01)` | 2026-09-02 | `docs/roadmap/issue-AR-355-working-agreements-resident-manager.md#implementation-2026-09-01` |
| 2 | test | `test_resident_kernel_is_compact_versioned_and_content_addressed` | 2026-09-02 | `tests/test_resident_managers.py:76-108` |
| 2 | file | `RESIDENT_MANAGER_KERNEL v5 text and hash` | 2026-09-02 | `agency_runtime/core/resident_managers.py:10-42` |
| 2 | file | `live binding receipt rmb-ab4a5952 / kernel=v5:62c94d87` | 2026-09-02 | `docs/roadmap/issue-AR-355-working-agreements-resident-manager.md:131-146` |
| 2 | receipt | `rmb-ab4a5952064a35bf4ae7dfeee6fd08f2` | 2026-09-02 | `rmb-ab4a5952064a35bf4ae7dfeee6fd08f2` |
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
| 1 | absent | `AR-355.1-20260902-57c62a71` | `91459bd9eb89c777695c5c195196be184f29f1438db203e5f772bf81aa33e2b1` | 2026-09-02 | The excerpts prove owner-configurable rendering and a Hermes fail-open path, but provide no direct artifact demonstrating staffed and unstaffed delivery on each of all four hosts; the roadmap prose only asserts that verification. |
| 2 | absent | `AR-355.2-20260902-4d449205` | `3d74cc488b29df4cfaa1cd19d64db8e04fd8b4dea5fa9d32d05f1cee0d7835ff` | 2026-09-02 | The source excerpt shows roster awareness between delegation-neutrality and anti-self-staffing, but the cited live receipt and its kernel hash and delivery details are not provided, so the live-observed requirement cannot be verified. |
| 3 | satisfied | `AR-355.3-20260902-95b89306` | `0251479f4b115cc0400af177de4bee2b0df3565198f0e00fb860d60e4b3cca19` | 2026-09-02 | The roadmap excerpt documents the v4-to-v5 re-wire, deploy projection, four green batteries, and operator_policy resolution, while the binding excerpt emits managers and the versioned kernel content hash. |
| 4 | satisfied | `AR-355.4-20260902-c47479d9` | `f85c7bb61da2804611313cb975093c510848188331c2237616172e7672321ff3` | 2026-09-02 | The roadmap acceptance excerpt records all stated measurements, while context_budget.py shows renderer-based component sizing and the cited tests verify AR-355 deltas, fail-open totals, staffed capsule replay, and CLI output. |
