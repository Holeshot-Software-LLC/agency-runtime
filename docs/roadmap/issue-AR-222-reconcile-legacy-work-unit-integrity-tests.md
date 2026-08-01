---
title: "AR-222: Reconcile legacy work-unit integrity tests"
status: open
category: roadmap
created: 2026-08-01
updated: 2026-08-01
tags: [bug, testing, delegation, compatibility]
related:
  - agency_runtime/core/unit_assignment.py
  - tests/test_work_unit_integrity.py
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: testing
issue_id: AR-222
priority: p2
tracker_url: null
depends_on: []
blocks: []
---

# AR-222: Reconcile legacy work-unit integrity tests

## Problem

Seven cases in `tests/test_work_unit_integrity.py` expect
`build_unit_agent_plan` to construct current plan rows from the legacy
`work_units.units` shape alone. The current planner returns no rows for that
fixture, so identity, dependency, parallelization, hydration, and duplicate-goal
assertions fail downstream.

## Current state

The failure was exposed by an optional AR-221 compatibility slice. Fourteen
tests ran: seven passed and seven failed. Both
`agency_runtime/core/unit_assignment.py` and `tests/test_work_unit_integrity.py`
are byte-for-byte unchanged from `origin/main`, so the result is not caused by
AR-221's Codex product wait or workspace-scope repair. The named production
spine does not include this file. AR-221 records the finding without expanding
its bounded product package.

## Approach

1. Determine whether the legacy fixture should be upgraded to the current
   verified workforce binding contract or whether a supported legacy adapter
   is still required.
2. Preserve full-goal identity, resource serialization, and fail-closed
   hydration in either path.
3. Run the file alone and add it to an appropriate maintained gate only after
   its intended contract is explicit.

## Dependencies

None. This is independent of the AR-221 live README product proof.

## Acceptance

- [ ] The supported legacy/current contract is explicit and documented.
- [ ] All fourteen work-unit integrity tests pass without deterministic
  specialist selection or weakening current plan validation.
- [ ] Focused lint, format, and relevant delegation checks pass.
