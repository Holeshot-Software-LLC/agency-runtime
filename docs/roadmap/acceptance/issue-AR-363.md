---
title: "AR-363 acceptance verification record"
status: active
category: roadmap
created: 2026-09-02
updated: 2026-09-02
tags: [acceptance, verification]
related:
  - docs/roadmap/issue-AR-363-deployed-fix-witness-manifests.md
supersedes: []
superseded_by: null
type: acceptance-verification
issue_id: AR-363
candidate_commit: 07043c0aa1f0e1740a5ad9b25bbaa7321bbbee12
evidence_cutoff: 2026-09-02
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/436
---

# AR-363 acceptance verification record

Deployed-fix witness manifests: builder evidence cited by the integrator against the merged
candidate `07043c0a`; every verdict below comes from one isolated
single-check verifier run (`scripts/verify_acceptance.py`, codex transport)
that saw only that criterion and its own rows.

## Builder evidence

| Criterion | Kind | Artifact | Observed | Source |
|---|---|---|---|---|
| 1 | test | `test_witness_drift_fails_a_host_whose_canary_passed` | 2026-09-01 | `tests/test_harness_battery.py:570-586` |
| 1 | test | `test_a_projection_missing_one_marker_is_missing_fix_and_names_it` | 2026-09-01 | `tests/test_deployed_fix_witness.py:235-252` |
| 1 | test | `test_an_unmeasured_host_falls_back_to_the_installed_pointer_and_says_so` | 2026-09-01 | `tests/test_deployed_fix_witness.py:305-320` |
| 1 | file | `attest_host` | 2026-09-01 | `agency_runtime/core/deployed_fix_witness.py:449-504` |
| 1 | file | `_witness_detail` | 2026-09-01 | `agency_runtime/core/harness_battery.py:696-711` |
| 1 | file | `run_battery witness outcome flip` | 2026-09-01 | `agency_runtime/core/harness_battery.py:760-780` |
| 1 | test | `test_an_unavailable_witness_never_flips_a_passing_host` | 2026-09-01 | `tests/test_harness_battery.py:589-602` |
| 2 | test | `test_the_stale_hook_shape_is_detected_as_drift` | 2026-09-01 | `tests/test_deployed_fix_witness.py:193-216` |
| 2 | test | `test_drift_is_reported_even_when_the_invoked_projection_is_gone` | 2026-09-01 | `tests/test_deployed_fix_witness.py:219-232` |
| 3 | test | `test_history_appends_one_line_per_attestation_newest_last_and_bounded` | 2026-09-01 | `tests/test_deployed_fix_witness.py:271-302` |
| 3 | file | `witness_history` | 2026-09-01 | `agency_runtime/core/deployed_fix_witness.py:565-612` |
| 3 | test | `test_a_full_history_is_rotated_so_the_newest_window_survives` | 2026-09-01 | `tests/test_deployed_fix_witness.py:436-451` |
| 3 | file | `_rotate_full_history` | 2026-09-01 | `agency_runtime/core/deployed_fix_witness.py:523-537` |

## Verification

| Criterion | Verdict | Verifier run | Evidence digest | Observed | Reason |
|---|---|---|---|---|---|
| 1 | satisfied | `AR-363.1-20260902-d50acd07` | `8222934186c15489073d92581d8a29c521fbb1a921569b50ed6854adc37a0711` | 2026-09-02 | attest_host verifies registry markers, _witness_detail runs it at battery time, the outcome logic fails passing hosts on witness failure, and cited tests demonstrate drift failure, named missing markers, pointer fallback, and unavailable handling. |
| 2 | satisfied | `AR-363.2-20260902-2c3b1c0f` | `0092a87140fa14dfcffee5d13045d8f1b831104e482faf09939101fb225ebf56` | 2026-09-02 | The cited test excerpts explicitly construct wired OLD versus published NEW and assert drift with published_projection_mismatch, including drift when the wired projection is missing. |
| 3 | satisfied | `AR-363.3-20260902-f314d2f0` | `e848735b240d287063041788f700d70227716d9dc5899f6a4c711bb57e3dc12c` | 2026-09-02 | The excerpts show per-host JSONL attestations appended newest-last, AR-345 flipping from true to false at the regression, bounded retrieval, and rotation preserving the newest history window. |
