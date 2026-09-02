---
title: "AR-354 acceptance verification record"
status: active
category: roadmap
created: 2026-09-02
updated: 2026-09-02
tags: [acceptance, verification]
related:
  - docs/roadmap/issue-AR-354-host-cli-coverage-suite-failing-on-main.md
supersedes: []
superseded_by: null
type: acceptance-verification
issue_id: AR-354
candidate_commit: f968aa213bdd0ca5edb1a0f1f41fa1279aed4e8a
evidence_cutoff: 2026-09-02
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/420
---

# AR-354 acceptance verification record

Host-CLI coverage suite repair: builder evidence cited by the integrator against the merged
candidate `f968aa21` (the repair plus the regenerated evidence file); every verdict below comes from one isolated
single-check verifier run (`scripts/verify_acceptance.py`, codex transport)
that saw only that criterion and its own rows.

## Builder evidence

| Criterion | Kind | Artifact | Observed | Source |
|---|---|---|---|---|
| 1 | command-output | `pytest: 108 passed across the three repaired suites; the four named tests PASSED` | 2026-09-02 | `docs/roadmap/acceptance/evidence/AR-354-pytest-20260902.txt:1-13` |
| 1 | test | `test_hook_stdio_constructs_explicit_store` | 2026-09-02 | `tests/test_coverage_final_host_cli.py:305-336` |
| 1 | test | `test_install_preflight_human_error_and_per_host_exception` | 2026-09-02 | `tests/test_coverage_final_host_cli.py:461-524` |
| 1 | test | `test_openclaw_finish_commit_and_outbound_state_fail_closed` | 2026-09-02 | `tests/test_coverage_final_host_cli.py:900-947` |
| 1 | test | `test_openclaw_persistence_runtime_disabled_and_constructor_matrix` | 2026-09-02 | `tests/test_coverage_final_host_cli.py:1038-1069` |
| 1 | file | `drift-by-commit diagnosis` | 2026-09-02 | `docs/roadmap/issue-AR-354-host-cli-coverage-suite-failing-on-main.md#implementation-2026-09-02` |
| 2 | file | `PRODUCTION_SPINE gains both suites` | 2026-09-02 | `scripts/run_local_gates.py:70-77` |
| 2 | file | `AGENTS.md validation block` | 2026-09-02 | `AGENTS.md:178-184` |
| 2 | file | `ci.yml fast-spine step` | 2026-09-02 | `.github/workflows/ci.yml:238-245` |
| 2 | file | `spine decision recorded` | 2026-09-02 | `docs/roadmap/issue-AR-354-host-cli-coverage-suite-failing-on-main.md#implementation-2026-09-02` |

## Verification

| Criterion | Verdict | Verifier run | Evidence digest | Observed | Reason |
|---|---|---|---|---|---|
| 1 | satisfied | `AR-354.1-20260902-718dec04` | `e16a469fccebddc1c6407549ea429ed55bd333b9bf12b05d66d4bd6b9755f451` | 2026-09-02 | The pytest artifact records all four named tests passing on main, while the test excerpts and AR-354 implementation record show repaired fixtures and identify each drift with its introducing commit. |
| 2 | satisfied | `AR-354.2-20260902-014eb0c7` | `b13b64646176620f50f6da3dbc5dab79614791d1da402b44139d1e466628eb72` | 2026-09-02 | The cited excerpts show both suites in PRODUCTION_SPINE and the AGENTS.md validation command, while the roadmap implementation explicitly records the fast-spine decision. |
