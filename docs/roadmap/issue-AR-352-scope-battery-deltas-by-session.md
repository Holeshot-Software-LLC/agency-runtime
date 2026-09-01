---
title: "AR-352: The ordinary battery counts other sessions' preflight failures as its own"
status: done
category: roadmap
created: 2026-09-01
updated: 2026-09-01
tags: [battery, reliability, evidence, false-negative]
related:
  - docs/roadmap/issue-AR-337-run-harness-battery-on-version-change.md
  - docs/roadmap/issue-AR-340-observe-npm-shim-harness-versions-in-battery.md
  - docs/roadmap/issue-AR-360-battery-pass-k-grading.md
supersedes: []
superseded_by: null
type: issue
epic: reliability
issue_id: AR-352
priority: p2
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/416
depends_on: []
blocks: []
---

# AR-352: The ordinary battery counts other sessions' preflight failures as its own

## Problem

`_run_ordinary_battery` (`agency_runtime/core/harness_battery.py`)
computes a global before/after delta over `recent_runtime_activity` and
fails the battery when ANY new `preflight_failures` row appears in its
window, regardless of which session or host produced it. On a busy box
this makes clean windows rare: during the 2026-09-01 deploy, hermes
battery runs whose own turns provably staffed and finalized
(`routing: 1, specialists: 1-2, finalizations: 2` in the battery's own
`new_row_counts`) were flipped to `ordinary_turn_not_staffing_complete`
by absorbed failures from an openclaw cron session (18:06:42Z), from
the interactive claude session running the deploy itself (18:32-18:33Z
hook turns), and from unrelated hermes sessions riding the intermittent
inference window (AR-353). The AR-338 capsule already documented the
same absorption on the Windows box ("the canary receipt's new_ids delta
absorbs concurrent sessions' store writes... join receipts to
runs.session_id") as operator guidance; the battery itself never
learned it.

## Current state

Verdicts from busy windows are untrustworthy in the failing direction
(false negatives only; a pass is still meaningful). Operators must
manually join receipts to sessions before believing a failure.

## Approach

Identify the battery turn's own session(s) from the new `runs` rows for
the battery's host, and evaluate `zero_preflight` (and ideally the
staffed-row minimums) against rows belonging to those sessions only.
Keep a separate informational count of absorbed foreign-session
activity in the report.

## Dependencies

None.

## Implementation (2026-09-01)

Landed in `agency_runtime/core/harness_battery.py` on the same branch as
AR-360 (the two share the ordinary probe's delta computation).

- `_run_ordinary_battery` no longer collapses the window to id sets. The
  before/after delta goes through `_new_activity_rows` and
  `_scope_activity_delta`; `_own_turn_keys` derives the battery turn's own
  session(s) from the new `runs` rows whose `host` equals the battery host.
  Both `session_id` and `trace_id` are kept as join keys: `finalizations`
  carry only a trace id, and every row of the turn shares its trace even
  when written before the run row exists. A row is own when either key
  matches; everything else is foreign.
- The verdict reads own rows only: own `runs >= 1`, own `routing >= 1`, own
  `specialists >= 1`, own `preflight_failures == 0`, plus exit 0 and no
  timeout. This closes the false negative (a foreign preflight failure no
  longer flips a staffed, finalized turn) and the mirror false positive the
  old global delta allowed (another session's routing and specialist rows
  can no longer staff a bare battery turn).
- Report detail per trial: `own_sessions` (bounded to 16 ids of at most
  128 chars), `own_session_row_counts` (drives the verdict),
  `foreign_session_activity` (count per collection),
  `foreign_session_hosts` (count per known host token; `unknown` when a
  row carries no host, `other` for anything outside the known host set, so
  free text never reaches the receipt), and `new_row_counts`, which keeps
  its pre-AR-352 meaning of every new row in the window regardless of
  session.
- Residual limitation, by design: a concurrent *new* session of the same
  host in the same window (an openclaw cron turn starting during the
  openclaw battery) is indistinguishable from the battery's own turn,
  because the harness CLI never reports the session it opened. Its preflight
  failure would still count. `own_sessions` with more than one entry makes
  the ambiguity visible in the receipt, and AR-360's pass@k grading of the
  ordinary probe is the mitigation.
- Tests (`tests/test_harness_battery.py`):
  `test_ordinary_battery_ignores_foreign_session_preflight_failures`
  (failures from a claude deploy session, another hermes session, an
  openclaw cron session, and an unknown host all absorbed as foreign),
  `test_ordinary_battery_fails_on_its_own_sessions_preflight_failure`
  (session join and trace-only join),
  `test_ordinary_battery_does_not_borrow_foreign_staffing_rows`, the
  updated `test_ordinary_battery_requires_staffing_complete_store_delta`,
  and cross-trial non-double-counting inside
  `test_flaky_ordinary_probe_passes_under_pass_any_k_and_records_every_trial`.
- Evidence scope: stage-ready (unit and end-to-end against a simulated
  store and runner). No live `agency battery` ran in this package; the
  first busy-window hermes or openclaw battery on the Linux box after
  deploy is the live proof to append here, and its receipt now shows the
  own/foreign split directly.

## Acceptance

- [x] A battery turn that staffs and finalizes passes even when another
      session (any host, including the operator's interactive session)
      records a preflight failure in the same window
      (`test_ordinary_battery_ignores_foreign_session_preflight_failures`).
- [x] A preflight failure belonging to the battery turn's own session
      still fails the battery
      (`test_ordinary_battery_fails_on_its_own_sessions_preflight_failure`).
- [x] The report distinguishes own-session rows from absorbed
      foreign-session activity (`own_sessions`, `own_session_row_counts`,
      `foreign_session_activity`, `foreign_session_hosts`; asserted in the
      two tests above and in
      `test_ordinary_battery_does_not_borrow_foreign_staffing_rows`).
- [x] Regression tests cover both scoping directions (the three tests
      above; `python3 -m pytest tests/test_harness_battery.py -q -W error`).
