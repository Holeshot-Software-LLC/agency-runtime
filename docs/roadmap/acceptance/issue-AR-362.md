---
title: "AR-362 acceptance verification record"
status: active
category: roadmap
created: 2026-09-02
updated: 2026-09-02
tags: [acceptance, verification]
related:
  - docs/roadmap/issue-AR-362-agent-chaos-harness-oracles.md
supersedes: []
superseded_by: null
type: acceptance-verification
issue_id: AR-362
candidate_commit: 82d4134019f3ce85281d55b0ca1022c6ba1744d2
evidence_cutoff: 2026-09-02
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/435
---

# AR-362 acceptance verification record

Agent-chaos harness with explicit oracles: builder evidence cited by the integrator against the merged
candidate `82d41340`; every verdict below comes from one isolated
single-check verifier run (`scripts/verify_acceptance.py`, codex transport)
that saw only that criterion and its own rows.

## Builder evidence

| Criterion | Kind | Artifact | Observed | Source |
|---|---|---|---|---|
| 1 | test | `test_the_shipped_experiments_pass_against_shipped_behaviour` | 2026-09-02 | `tests/test_chaos_harness.py:72-95` |
| 1 | test | `test_staffing_window_covers_the_three_measured_shapes` | 2026-09-02 | `tests/test_chaos_harness.py:98-102` |
| 1 | file | `_staffing_findings (the oracle's checks)` | 2026-09-02 | `agency_runtime/core/chaos/experiments.py:356-395` |
| 1 | file | `STAFFING_WINDOW experiment` | 2026-09-02 | `agency_runtime/core/chaos/experiments.py:413-441` |
| 1 | receipt | `live run receipt 20260902T045234355398Z-staffing_window` | 2026-09-02 | `20260902T045234355398Z-staffing_window` |
| 1 | file | `live run recorded` | 2026-09-02 | `docs/roadmap/issue-AR-362-agent-chaos-harness-oracles.md#implementation-2026-09-02` |
| 2 | file | `_hard_kill_findings (recovery oracle)` | 2026-09-02 | `agency_runtime/core/chaos/experiments.py:797-844` |
| 2 | file | `_HARD_KILL_GAP_NOTES (the documented gap)` | 2026-09-02 | `agency_runtime/core/chaos/experiments.py:456-470` |
| 2 | file | `RUNNER_HARD_KILL experiment` | 2026-09-02 | `agency_runtime/core/chaos/experiments.py:862-890` |
| 2 | test | `test_the_shipped_experiments_pass_against_shipped_behaviour (gap notes asserted)` | 2026-09-02 | `tests/test_chaos_harness.py:72-95` |
| 2 | receipt | `live run receipt 20260902T045240653999Z-runner_hard_kill` | 2026-09-02 | `20260902T045240653999Z-runner_hard_kill` |
| 3 | file | `arm_safety (dedicated home, dedicated store, gate, rollback)` | 2026-09-02 | `agency_runtime/core/chaos/safety.py:193-230` |
| 3 | file | `ChaosEnvelope.open_store / require_session / require_armed` | 2026-09-02 | `agency_runtime/core/chaos/safety.py:82-150` |
| 3 | test | `test_safety_refuses_the_live_database_and_foreign_sessions` | 2026-09-02 | `tests/test_chaos_harness.py:105-122` |
| 3 | test | `test_effects_apply_only_inside_an_armed_envelope` | 2026-09-02 | `tests/test_chaos_harness.py:125-130` |
| 3 | test | `test_a_raising_effect_is_a_failed_receipt_and_still_rolls_back` | 2026-09-02 | `tests/test_chaos_harness.py:133-153` |
| 3 | test | `test_actions_see_only_chaos_sessions_and_the_dedicated_store` | 2026-09-02 | `tests/test_chaos_harness.py:176-200` |

## Verification

| Criterion | Verdict | Verifier run | Evidence digest | Observed | Reason |
|---|---|---|---|---|---|
| 1 | satisfied | `AR-362.1-20260902-927c3a4f` | `007109ae9124c62c8df62691581498828e043c20895a51d6120dac439c3c780d` | 2026-09-02 | The experiment excerpt defines on-demand injection and a three-case oracle, the test excerpts assert all three shapes and a passing shipped-behavior verdict, and the roadmap excerpt records the 2026-09-02 live staffing_window receipt as passing. |
| 2 | satisfied | `AR-362.2-20260902-05c3ef96` | `ca801a02694d3ecae7a69b69c406ec5c6a894ca74dcda11e7fa184b7b42c20eb` | 2026-09-02 | The experiment definition names runner_hard_kill, its oracle checks active/in_progress lease-lapse recovery, _HARD_KILL_GAP_NOTES contains four notes, and the shipped-behavior test asserts a PASS verdict. |
| 3 | satisfied | `AR-362.3-20260902-852480f5` | `05fcbf00eb5f63d1d8fec582baf554bc35e002cb8bbb68ab19258e4840921b5a` | 2026-09-02 | The cited code enforces an armed gate, dedicated runtime home and store, chaos-only session prefix, live-database refusal, and cleanup on exit; the cited tests verify each boundary and rollback after an exception. |
