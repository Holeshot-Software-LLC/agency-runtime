---
title: "AR-352: The ordinary battery counts other sessions' preflight failures as its own"
status: open
category: roadmap
created: 2026-09-01
updated: 2026-09-01
tags: [battery, reliability, evidence, false-negative]
related:
  - docs/roadmap/issue-AR-337-run-harness-battery-on-version-change.md
  - docs/roadmap/issue-AR-340-observe-npm-shim-harness-versions-in-battery.md
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

## Acceptance

- [ ] A battery turn that staffs and finalizes passes even when another
      session (any host, including the operator's interactive session)
      records a preflight failure in the same window.
- [ ] A preflight failure belonging to the battery turn's own session
      still fails the battery.
- [ ] The report distinguishes own-session rows from absorbed
      foreign-session activity.
- [ ] Regression tests cover both scoping directions.
