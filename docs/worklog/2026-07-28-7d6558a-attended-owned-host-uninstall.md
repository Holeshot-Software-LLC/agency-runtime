---
title: "Worklog detail: Add attended owned host uninstall"
status: active
category: worklog
created: 2026-07-28
updated: 2026-07-28
tags: [uninstall, cli, host-integrations, security, recovery]
related:
  - docs/roadmap/issue-AR-189-add-owned-host-integration-uninstall.md
  - docs/decisions/0108-retire-only-owned-host-integrations.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: worklog
commit: 7d6558a15d81162331e2f9e164b9691de1a94576
short: 7d6558a
date: 2026-07-28
pr: null
related_issues:
  - docs/roadmap/issue-AR-189-add-owned-host-integration-uninstall.md
---

# Worklog detail: Add attended owned host uninstall

## Purpose

Give operators one reversible command that discovers Agency Runtime integrations
across all five supported harnesses and detaches only integrations whose exact
ownership can be proven, without conflating host cleanup with package or data
removal.

## Approach

The implementation adds a write-free planning mode and requires the exact plan
digest plus native Windows operator presence for application. It binds the
managed tree, complete prepared launcher chain, native registration evidence,
runtime context, deterministic retention destination, and preservation policy.
All Agency host-lifecycle writers share one private lock and revalidate before
mutation. Native detachment is proven before the unchanged owned bundle is
retained, with a PowerShell-safe exact-backup recovery command.

The dashboard remains observation-only: it can copy the fixed all-host dry-run
command but cannot apply uninstall. ADR-0108 records the durable ownership,
authority, preservation, and recovery boundary.

## Challenges encountered

The review found path substitution, incomplete launcher binding, ambiguous
native path aliases, premature operation journaling, lifecycle-writer races,
and Windows recovery-command quoting risks. These were repaired and covered by
focused regressions. ZCode cannot provide filesystem compare-and-swap against
an external same-account writer, so that final read-to-replace interval remains
an explicit documented operational residual.

## Decisions and alternatives

[ADR-0108](../decisions/0108-retire-only-owned-host-integrations.md) rejects
recursive deletion, marketplace removal without exclusive ownership evidence,
unattended application, and dashboard/MCP mutation. Successful uninstall keeps
Agency configuration, Store, roster, evidence, backups, package, dashboard
service, marketplace registrations, and unrelated host configuration.

## Verification

- The comprehensive focused uninstall, parser, operator-presence, and native
  asset slice passed 287 tests in 28.86 seconds.
- The final host-only suite passed 31 tests after PowerShell recovery rendering.
- Generic install/rollback/toggle locking passed 24 selected tests; the prepared
  Codex lifecycle-lock regression passed independently.
- All 109 dashboard UI tests passed.
- Ruff check and format, documentation validation for 485 files, and whitespace
  checks passed.
- Independent security and trace reviews found no critical or high uninstall
  findings after the final fixes.

## Follow-ups

- Run the write-free all-host plan from the clean checkpoint and record the live
  inventory result in [AR-189](../roadmap/issue-AR-189-add-owned-host-integration-uninstall.md).
- Same-repository tracker creation remains pending explicit outward
  authorization.
- The external same-account ZCode writer interval remains an operating
  constraint; stop ZCode before applying uninstall.
