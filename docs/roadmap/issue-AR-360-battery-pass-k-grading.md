---
title: "AR-360: Grade harness batteries with pass@k and pass^k trial semantics"
status: done
category: roadmap
created: 2026-09-01
updated: 2026-09-01
tags: [battery, reliability, flakiness, grading]
related:
  - docs/roadmap/issue-AR-352-scope-battery-deltas-by-session.md
  - docs/roadmap/issue-AR-353-intermittent-staffing-verdict-window-linux.md
  - docs/roadmap/issue-AR-337-run-harness-battery-on-version-change.md
supersedes: []
superseded_by: null
type: issue
epic: reliability
issue_id: AR-360
priority: p2
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/433
depends_on: []
blocks: []
---

# AR-360: Grade harness batteries with pass@k and pass^k trial semantics

## Problem

The harness battery renders a single-shot verdict per host, so a flaky
window (AR-353) produces reds that operators overturn by ad-hoc rerun
("retry until green"), and a genuinely intermittent regression can slip
through on a lucky single pass. Both 2026-09-01 deploys hit this:
hermes failed its first attempt and passed the second, with no recorded
basis for preferring either result.

## Current state

`agency battery` runs each host once; the report has no notion of
trials. Operator lore ("hermes flaps ~50%, retry once") lives in
session memory instead of the product.

## Approach

Adopt the k-trial semantics from eval-driven development (lifted from
ECC's eval-harness skill, owner-approved 2026-09-01):

- Safety-critical checks (wiring trust, hook activation, finalization
  round-trip) grade as **pass^k** — k independent trials, all green.
- Checks overlapping known-flaky windows grade as **pass@k** — pass if
  any of k trials succeeds, with every trial recorded.
- The battery report names the grading mode and records each trial, so
  a flap is data (feeding AR-353 measurement) instead of noise.

Keep k small and configurable (default 2-3); single-trial remains valid
for cheap deterministic probes.

## Dependencies

- Complements AR-352 (per-session delta isolation) — trial recording
  should not double-count foreign-session failures.

## Implementation (2026-09-01)

Landed in `agency_runtime/core/harness_battery.py`,
`agency_runtime/cli/parser.py`, and `agency_runtime/core/doctor.py` on the
same branch as AR-352.

- Grading modes are plain ASCII data tokens: `pass_all_k` (documented as
  pass^k: every trial must pass) for the canary probes — claude and codex
  prove wiring trust, hook activation, and the finalization round-trip, so
  a single lucky pass must not prove a drifted harness — and `pass_any_k`
  (pass@k: any passing trial proves the harness) for the ordinary probes —
  hermes and openclaw overlap the intermittent staffing window (AR-353).
  `probe_grading_mode(host)` declares the mode. Version observation and the
  posture scan stay single-shot and deterministic; only the host turn is
  the graded check.
- `k`: `run_battery(..., trials=None)` goes through `validated_trials`
  (default `BATTERY_DEFAULT_TRIALS = 2`, bounded 1 through
  `BATTERY_MAX_TRIALS = 5`; bool, float, and string values are refused).
  `agency battery --trials N` (parser type `_battery_trials`, 1 through 5)
  is threaded by `run_battery_cli`; `--trials 1` is the single-shot battery
  for cheap deterministic probes.
- `_run_graded_probe` binds one host's single-trial probe (`_host_probe`;
  the store opens once per host and is shared by its trials) and runs every
  requested trial — a flap is exactly the measurement AR-353 needs — with
  one short-circuit: an `attended_trust_required` trial ends the series
  with that distinct outcome and reason (`codex_hook_trust_not_ready`),
  because retrying an attended step cannot change its answer. Each trial
  computes its own before/after store delta, so foreign-session activity is
  counted once, in the trial whose window absorbed it.
- Persistence: the host detail is `{mode, outcome, reason, grading:
  {mode, trials_requested, trials_run, passed_trials, failed_trials},
  trials: [per-trial detail plus trial number and ran_at]}`, sealed whole
  into the receipt; the fingerprint entry adds `last_grading_mode` and
  `last_trials {requested, run, passed}`; the battery report adds a
  top-level `trials`. Graded reasons name the failing trials:
  `pass_all_k_trial_failed:2`, `pass_any_k_all_trials_failed:1,2`.
- Doctor keeps its message contract; the tally rides as `CheckResult.detail`
  (`pass^2: 2/2 trials`). Entries written before grading, or with a
  malformed tally, render exactly as before.
- Human CLI line: `hermes: passed (pass@2: 1/2 trials) (Hermes Agent
  v0.21.0)`; a failed verdict appends its graded reason.
- Spend note: the default k=2 doubles a battery's host turns (every trial
  is a real turn within the existing canary and ordinary budgets), and the
  systemd trigger runs with the default. `--trials 1` restores the old
  spend where an operator wants it.
- Tests: `tests/test_harness_battery.py` —
  `test_grade_trials_folds_outcomes_per_mode`,
  `test_trial_count_is_bounded_and_grading_modes_follow_the_probe`,
  `test_flaky_ordinary_probe_passes_under_pass_any_k_and_records_every_trial`,
  `test_flaky_canary_probe_fails_under_pass_all_k_and_names_the_failing_trial`,
  `test_single_trial_grades_like_the_single_shot_battery`,
  `test_run_battery_rejects_out_of_range_trials`,
  `test_run_battery_cli_threads_trials_and_prints_the_grading_tally`, plus
  the attended short-circuit added to
  `test_failed_battery_keeps_prior_proof_and_reports_not_ok`, the default
  k=2 pinned in
  `test_run_battery_gates_on_change_updates_proof_and_seals_receipts`, and
  the doctor detail in `test_doctor_surfaces_last_battery_outcome_per_harness`;
  `tests/test_cli_parser_contract.py` —
  `test_battery_parser_bounds_trials_per_probe` and the refreshed golden
  manifest digest.
- Evidence scope: stage-ready with simulated runners and stores. No live
  battery ran in this package; the first deployed run records the first
  real flap statistics for AR-353.

## Acceptance

- [x] Battery checks declare a grading mode; safety-critical checks
      require pass^k and flaky-window checks report pass@k
      (`probe_grading_mode`;
      `test_trial_count_is_bounded_and_grading_modes_follow_the_probe`,
      `test_flaky_canary_probe_fails_under_pass_all_k_and_names_the_failing_trial`,
      `test_flaky_ordinary_probe_passes_under_pass_any_k_and_records_every_trial`).
- [x] Every trial outcome is persisted in the battery report (the `trials`
      array in the host detail and sealed receipt, `last_trials` in the
      fingerprint; asserted in both flaky tests and
      `test_run_battery_gates_on_change_updates_proof_and_seals_receipts`).
- [x] A simulated 50%-flaky check is graded correctly under both modes
      in regression tests (the alternating fail/pass runner in the two
      flaky tests plus `test_grade_trials_folds_outcomes_per_mode`;
      `python3 -m pytest tests/test_harness_battery.py -q -W error`).
