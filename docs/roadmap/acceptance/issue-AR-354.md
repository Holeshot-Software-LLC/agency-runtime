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
candidate_commit: 1cdc79ff4715ee981a0f8ffed6bfe25d22daf5e8
evidence_cutoff: 2026-09-02
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/420
---

# AR-354 acceptance verification record

Host-CLI coverage suite repair: builder evidence cited by the integrator against the merged
candidate `1cdc79ff`; every verdict below comes from one isolated
single-check verifier run (`scripts/verify_acceptance.py`, codex transport)
that saw only that criterion and its own rows.

## Builder evidence

| Criterion | Kind | Artifact | Observed | Source |
|---|---|---|---|---|
| 1 | test | `test_hook_stdio_constructs_explicit_store` | 2026-09-02 | `tests/test_coverage_final_host_cli.py:305-336` |
| 1 | test | `test_install_preflight_human_error_and_per_host_exception` | 2026-09-02 | `tests/test_coverage_final_host_cli.py:461-524` |
| 1 | test | `test_openclaw_finish_commit_and_outbound_state_fail_closed` | 2026-09-02 | `tests/test_coverage_final_host_cli.py:900-947` |
| 1 | test | `test_openclaw_persistence_runtime_disabled_and_constructor_matrix` | 2026-09-02 | `tests/test_coverage_final_host_cli.py:1038-1069` |
| 1 | test | `test_stop_publishes_when_persistent_delivery_cannot_be_acknowledged` | 2026-09-02 | `tests/test_resident_manager_lifecycle.py:628-658` |
| 1 | file | `drift-by-commit diagnosis` | 2026-09-02 | `docs/roadmap/issue-AR-354-host-cli-coverage-suite-failing-on-main.md#implementation-2026-09-02` |
| 2 | file | `PRODUCTION_SPINE gains both suites` | 2026-09-02 | `scripts/run_local_gates.py:70-77` |
| 2 | file | `AGENTS.md validation block` | 2026-09-02 | `AGENTS.md:178-184` |
| 2 | file | `ci.yml fast-spine step` | 2026-09-02 | `.github/workflows/ci.yml:238-245` |
| 2 | file | `spine decision recorded` | 2026-09-02 | `docs/roadmap/issue-AR-354-host-cli-coverage-suite-failing-on-main.md#implementation-2026-09-02` |

## Verification

| Criterion | Verdict | Verifier run | Evidence digest | Observed | Reason |
|---|---|---|---|---|---|
| 2 | satisfied | `AR-354.2-20260902-83179452` | `7b5d5ca201f7e7ca9ec188da5293a9ef9db0860cc039a1c06a2bd304edfdc5c3` | 2026-09-02 | The excerpts show both named suites in scripts/run_local_gates.py and the AGENTS.md validation block, while the roadmap implementation explicitly records the fast-spine decision. |
