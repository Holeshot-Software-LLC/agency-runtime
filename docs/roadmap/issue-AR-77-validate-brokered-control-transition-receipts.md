---
title: "AR-77: Validate brokered control transition receipts exactly"
status: done
category: roadmap
created: 2026-07-16
updated: 2026-07-17
tags: [security, operations, cli, dashboard, evidence, concurrency]
related:
  - docs/decisions/0053-durable-fail-enabled-master-control.md
  - docs/decisions/0057-generation-checked-host-control-mutations.md
  - docs/decisions/0058-broker-restricted-windows-host-controls.md
  - docs/decisions/0061-validate-brokered-control-transition-receipts.md
  - docs/THREAT_MODEL.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: security
issue_id: AR-77
priority: p0
tracker_url: "https://github.com/Holeshot-Software-LLC/agency-runtime/issues/78"
depends_on: [AR-57, AR-70, AR-74]
blocks: []
---

# AR-77: Validate brokered control transition receipts exactly

## Problem

The CLI validates the shape of dashboard-brokered master and host-control
responses but does not prove their transition semantics. A stale or buggy
same-user service can return the opposite state, an unchanged generation for a
real transition, an arbitrary jump, or an impossible effective host state while
the CLI exits zero.

## Current state

The implementation now binds brokered master and host receipts to the previously
observed state and legal deterministic transition. Store-backed host receipts
also carry config and Store identity and reject restart-required drift.
Full-suite and installed restricted-Codex acceptance remain pending.

## Approach

Require top-level success and requested state. A no-op preserves generation; a
real transition increments exactly once. Bind host top-level and nested status
to that expected result and to the prior config path/revision, environment
override identity, and active/desired Store paths. Reject effective-enabled
truth whenever master or host runtime state is false. Treat stale, overflowed,
missing, opposite, Store-drifted, and jumping receipts as terminal without
automatic retry.

## Dependencies

AR-57 owns the master switch, AR-70 owns host CAS, and AR-74 owns restricted
brokerage. ADR-0061 makes receipt transition semantics part of the evidence
contract rather than an implementation assumption.

## Acceptance

- [x] Master-toggle receipts require success, requested state, and the legal generation transition.
- [x] Host-toggle receipts require legal no-op/increment semantics in top-level and nested status.
- [x] Brokered host status rejects impossible effective state.
- [x] Stale, opposite, missing, malformed, overflow, and generation-jump receipts fail without retry.
- [x] Focused protocol tests and exact coverage pass.
- [x] Installed smoke, tracker, and merged-install gates pass.
