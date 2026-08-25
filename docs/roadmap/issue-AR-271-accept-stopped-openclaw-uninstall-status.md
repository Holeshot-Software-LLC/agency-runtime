---
title: "Accept stopped OpenClaw uninstall status"
status: open
category: roadmap
created: 2026-08-21
updated: 2026-08-21
tags: [openclaw, uninstall, gateway, compatibility]
related:
  - docs/roadmap/issue-AR-285-accept-openclaw-stopped-gateway-status.md
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/handoffs/issue-AR-119.md
  - agency_runtime/core/installer_uninstall.py
supersedes: []
superseded_by: null
type: issue
epic: install
issue_id: AR-271
priority: p0
tracker_url: null
depends_on: []
blocks: []
---

# AR-271: Accept stopped OpenClaw uninstall status

## Problem

OpenClaw `gateway status --deep --require-rpc --json` returns exit 1 when the
gateway is stopped and places the authoritative stopped facts in nested service
state. The install classifier now accepts that exact bounded shape under
AR-285, but the separate uninstall classifier still requires exit 0 and
top-level status, so safe rollback is blocked even after a native stop.

## Current state

The post-plugin-removal dry-run is preserved as
`OpenClaw gateway state is unproven; uninstall is blocked`. Systemd separately
proved the unit inactive. Recovery invoked the checked-in transactional
prior-delivery restore only after proving both gateway inactivity and plugin
absence; all five retained streaming values were restored and verified.

## Approach

Share or mirror the bounded stopped-state classifier used by installation.
Accept only complete, untruncated exit-1 receipts whose nested runtime state is
exactly stopped/inactive/dead. Keep live, partial, ambiguous, truncated, and
unknown receipts blocked.

## Dependencies

- AR-285 stopped-gateway classifier contract.
- Existing uninstall execution binding and final-state verification.

## Acceptance
