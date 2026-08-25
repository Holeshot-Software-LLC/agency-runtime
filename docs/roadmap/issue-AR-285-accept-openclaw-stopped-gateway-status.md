---
title: "AR-285: Accept OpenClaw stopped gateway status"
status: in_progress
category: roadmap
created: 2026-08-21
updated: 2026-08-21
tags: [openclaw, installer, compatibility, security, AR-119, AR-264]
related:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-264-compile-actionable-contractor-execution-profiles.md
  - docs/roadmap/AR-119-openclaw-hermes-verification-packet.md
  - docs/roadmap/handoffs/issue-AR-119.md
  - docs/roadmap/handoffs/issue-AR-264.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: install
issue_id: AR-285
priority: p0
tracker_url: null
depends_on: []
blocks: []
---

# AR-285: Accept OpenClaw stopped gateway status

## Problem

OpenClaw 2026.7.1-2 returns complete JSON from `gateway status --deep
--require-rpc --json` while a systemd gateway is stopped, but exits 1 because
the stopped process cannot answer the required RPC probe. The process state is
nested at `service.runtime` rather than the older top-level fields. Agency
discarded every nonzero result before parsing that explicit stopped state, so
the installer classified a safely stopped gateway as unknown and refused all
mutation.

## Current state

- The audited OpenClaw 2026.7.1-2 host was stopped through its native service
  lifecycle before installation.
- Its native status receipt reports the internally consistent process-state
  triple `stopped` / `inactive` / `dead`, an unavailable RPC endpoint, and exit
  code 1.
- The first installer dry run correctly rejected a group-writable executable;
  the second correctly rejected its group-writable parent namespace. After
  tightening only those user-owned paths, the third dry run reached this
  compatibility defect and made no installation changes.
- A focused regression reproduces the exact nested, nonzero native receipt. It
  failed before the repair because Agency returned unknown and now passes with
  the bounded classifier change.
- Tracker creation is pending explicit authorization; no outward-facing write
  is authorized in the current Linux package.

## Approach

Parse a complete bounded JSON receipt even when the native command exits
nonzero, but retain fail-closed treatment for truncated, malformed, ambiguous,
or contradictory output. Live nested process states continue to block. A
nonzero result proves stopped only for OpenClaw's expected exit code 1 and the
exact internally consistent `stopped` / `inactive` / `dead` runtime triple.
Preserve the older successful top-level status contract unchanged.

## Dependencies

- AR-119 owns truthful installed and live host evidence.
- AR-264 owns the current Linux OpenClaw/Hermes verification package.
- The executable namespace and live-gateway safety gates remain authoritative;
  this issue changes neither policy nor restart authority.

## Acceptance

- [x] A focused regression first reproduces the real OpenClaw 2026.7.1-2
      nested stopped receipt and fails against the unmodified classifier.
- [x] Complete exit-1 JSON with `stopped` / `inactive` / `dead` is classified
      as stopped without relaxing executable or namespace trust.
- [x] Truncated, malformed, ambiguous, contradictory, and other nonzero native
      results remain unproven; explicit live states remain blocking.
- [x] The changed checkout passes the focused OpenClaw installer suite.
- [x] A changed-precondition dry run and real install pass while the gateway
      remains stopped, and the installer does not restart it.
