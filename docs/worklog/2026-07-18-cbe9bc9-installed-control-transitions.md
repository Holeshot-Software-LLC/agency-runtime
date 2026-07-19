---
title: "Worklog detail: Harden installed control transitions"
status: active
category: worklog
created: 2026-07-18
updated: 2026-07-18
tags: [dashboard, windows, runtime-control, operations, delegation]
related:
  - docs/roadmap/README.md
  - docs/decisions/0031-optional-user-dashboard-service-and-shared-configuration.md
  - docs/decisions/0051-bind-dashboard-runtime-publication-to-validated-filesystem-identities.md
  - docs/decisions/0053-durable-fail-enabled-master-control.md
  - docs/decisions/0060-restricted-windows-cli-read-and-fail-safe.md
supersedes: []
superseded_by: null
type: worklog
commit: cbe9bc9b7760ab0191217d1091b9b6c6ee116852
short: cbe9bc9
date: 2026-07-18
pr: null
related_issues:
  - docs/roadmap/issue-AR-89-operational-roster-inference-parity.md
  - docs/roadmap/issue-AR-100-wait-for-windows-dashboard-runtime-exit.md
  - docs/roadmap/issue-AR-101-enforce-restricted-global-master-switch.md
---

# Worklog detail: Harden installed control transitions

## Purpose

Close three gaps exposed by the committed-artifact smoke test: Windows Task
Scheduler could report idle before the old dashboard worker released its
descriptor, a restricted Codex process could ignore a deliberate global-off
state, and CLI status did not expose the same bounded inference evidence as the
dashboard.

## Approach

Windows service transitions now wait for the exact captured runtime generation
to clear and preserve any replacement generation as an explicit conflict.
Restricted canonical consumers use the authenticated dashboard only when local
integrity proof is unavailable, while custom identities and malformed evidence
remain fail-enabled. Hooks, HTTP, MCP, and CLI operations reuse one authoritative
master snapshot. CLI status and Route Lab share bounded operational projections
for inference health and recommendation-only unit-to-specialist plans.

## Challenges encountered

The service-manager idle transition is not the same event as worker exit. The
first clearance design also risked treating a replacement descriptor as proof
that the old worker was gone, so the final design reports that race as unknown
and never cleans up the replacement. The restricted master fix had to preserve
the sandbox integrity boundary and avoid recursive dashboard brokerage.

## Decisions and alternatives

An unconditional wait or fingerprint-change success test was rejected because
either could hang installation or erase a concurrent replacement. Weakening the
restricted filesystem validator was rejected because a sandbox must not be able
to forge disabled state. Dashboard projections are recommendation evidence only;
they never claim that native delegation executed.

## Verification

- Quarantine, remediation, bundled-roster, and sync regressions: 408 passed.
- Integrated runtime-control, dashboard-service, CLI, HTTP, MCP, and routing regressions: 704 passed, 4 skipped.
- Dashboard UI regressions: 88 passed.
- Ruff check, Ruff format, documentation validation, metadata, worklog, and diff checks passed.

## Follow-ups

Build and reinstall the final committed artifacts, repeat the real Windows
service and restricted off/on smoke, run the complete release matrix, and
record the pull request before tracker closure.
