---
title: "AR-67: Require explicit native enablement proof"
status: done
category: roadmap
created: 2026-07-16
updated: 2026-07-16
tags: [hosts, installation, evidence, claude, hermes, testing]
related:
  - docs/decisions/0028-host-support-maturity-and-reversible-install.md
  - docs/decisions/0036-capability-bound-host-canary-attestations.md
  - docs/roadmap/issue-AR-03-supported-host-integrations.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: host-integrations
issue_id: AR-67
priority: p0
tracker_url: "https://github.com/Holeshot-Software-LLC/agency-runtime/issues/68"
depends_on: []
blocks: []
---

# AR-67: Require explicit native enablement proof

## Problem

Hermes and Claude Code registration treated a matching plugin inventory row
with no enablement field as proof that the plugin was enabled. The success path
then persisted `enabled: true`, converting unknown native state into a false
installation and maturity claim.

## Current state

Both registration handlers now require the native inventory parser to return
literal `true`. An absent or malformed enablement field fails the verification
step while preserving the inventory row as unknown inspection evidence.

## Approach

Use the same explicit-boolean postcondition already enforced for Codex. Keep
registration, enablement, loading, and canary maturity separate, and add native
command-plan regressions for Hermes text inventory and Claude JSON inventory.

## Dependencies

ADR-0028 separates host discovery and registration maturity; ADR-0036 requires
capability-bound live evidence. This correction enforces those decisions at
the registration postcondition.

## Acceptance

- [x] Hermes inventory without explicit enabled state fails registration proof.
- [x] Claude inventory without explicit enabled state fails registration proof.
- [x] Explicit enabled and disabled states retain their existing behavior.
- [x] Failed proof cannot persist `registered: true` or `enabled: true`.
- [x] Native installer, host matrix, full-suite, exact-coverage, and installed smoke gates pass.
