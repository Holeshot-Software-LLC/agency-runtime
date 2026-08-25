---
title: "AR-292: Classify setup activation pending as degraded"
status: done
category: roadmap
created: 2026-08-25
updated: 2026-08-25
tags: [setup, install, codex, activation, cli, reliability]
related:
  - docs/roadmap/issue-AR-290-end-to-end-guided-setup.md
  - docs/roadmap/issue-AR-291-isolate-smoke-runtime-pointers.md
  - agency_runtime/cli/setup_commands.py
  - agency_runtime/cli/install_commands.py
  - tests/test_cli_setup.py
  - tests/test_cli_coverage_complete_install.py
  - README.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: install
issue_id: AR-292
priority: p0
tracker_url: null
depends_on: []
blocks: [AR-290]
---

# AR-292: Classify setup activation pending as degraded

## Problem

`agency install` deliberately withholds completion until Codex has current-
profile activation proof. The AR-290 setup orchestrator receives only that
strict exit code and currently labels every nonzero install result as a hard
mutation failure. On this machine, installed setup registered Codex, Claude,
ZCode, and the dashboard without residual runtime drift; doctor then reported
only truthful restart and Codex trust warnings, yet setup returned exit 1 and
printed `installation failed`.

That output tells a consumer to repair a mutation that succeeded and prevents
the wizard from reaching deterministic smoke. Treating every incomplete result
as success would be worse: staged-but-unregistered hosts, failed dashboards,
failed activation verification, and runtime drift must remain hard failures.

## Current state

- Standalone `agency install` has a strict completion contract and must retain
  it.
- An attended setup invocation always requests Codex installation without a
  live activation canary; the user must restart Codex and settle hook trust.
- The install command already has structured host, dashboard, activation, and
  residual-drift facts before reducing them to an exit code.
- Tracker creation is pending explicit authorization.

## Approach

Add an internal setup-only install option. Return degraded exit 2 only when the
dashboard and every host mutation are `ok`, the only incomplete host is a
registered Codex integration with exact attended `activation_required` state,
and no residual runtime drift exists. Preserve exit 1 for every other
incomplete or failed state and preserve the public standalone install behavior.

Teach setup to label exit 2 `activation-pending`, continue through doctor and
deterministic smoke, and return degraded if any accepted diagnostic stage was
degraded. Document the exit-code meanings for consumers.

## Dependencies

- AR-290 owns the guided setup journey.
- AR-291 removed the unrelated source-smoke pointer contamination, allowing
  this return-code mismatch to be isolated without residual drift.
- Codex hook trust remains an attended host-owned action.

## Acceptance

- [x] Exact successful attended Codex activation pending maps to setup-only
      exit 2 while standalone install remains strict.
- [x] Dashboard failure, failed host mutation, staged/unregistered host,
      activation verification failure, and residual drift remain exit 1.
- [x] Setup labels the stage `activation-pending`, runs requested deterministic
      smoke, and preserves any degraded stage in its final exit code.
- [x] Consumer README explains setup exits 0, 2, and 1 without overstating live
      host or release evidence.
- [x] Focused setup/install tests, Ruff, docs, and diff checks pass.
- [x] Installed guided setup returns 2 with activation pending and no hard stage
      failure or residual drift.
- [x] Tracker creation and linkage remain pending separate authorization.

## Verification evidence

The installed failure was reproduced after the AR-291 repaired smoke passed all
8 deterministic checks and proved the operator pointer set unchanged. No
foreign-package drift remained. The new regression group failed in the five
expected places before implementation, then passed all 58 focused tests. The
broader setup, install, native installer, doctor, parser, and dashboard-service
group passed all 299 tests with warnings as errors. Full Ruff lint and format,
metadata, policy, worklog, 815-file documentation, and diff checks pass. Exact
installed setup then registered Codex, Claude, and ZCode plus the dashboard,
reported no residual drift, and passed deterministic smoke 8/8. A final
idempotent pass captured native exit 2 and the exact
`installation: activation-pending` summary; configuration and doctor remained
truthfully degraded only for attended trust/restart state.
