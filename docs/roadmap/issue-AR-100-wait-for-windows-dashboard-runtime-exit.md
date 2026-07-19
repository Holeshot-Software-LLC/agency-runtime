---
title: "AR-100: Wait for the old Windows dashboard runtime to exit"
status: in_progress
category: roadmap
created: 2026-07-18
updated: 2026-07-18
tags: [dashboard, windows, service, lifecycle, reliability]
related:
  - docs/roadmap/issue-AR-13-optional-dashboard-service-configuration.md
  - docs/roadmap/issue-AR-98-validate-dashboard-service-launcher-status.md
  - docs/decisions/0031-optional-user-dashboard-service-and-shared-configuration.md
  - docs/decisions/0051-bind-dashboard-runtime-publication-to-validated-filesystem-identities.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: dashboard
issue_id: AR-100
priority: p0
tracker_url: "https://github.com/Holeshot-Software-LLC/agency-runtime/issues/101"
depends_on: []
blocks: []
---

# AR-100: Wait for the old Windows dashboard runtime to exit

## Problem

Windows dashboard reinstall waits for Task Scheduler to report its task idle,
then immediately checks the old authenticated runtime descriptor. The worker can
still be finishing after the manager state changes, so a legitimate shutdown
race makes transactional reinstall fail and roll back with “old dashboard
runtime remained reachable before activation.”

## Current state

The rebuilt real artifact reproduced this exact race, and rollback restored the
prior owned registration and restarted the service. Lifecycle transitions now
use a bounded generation-identity-safe clearance wait. A replacement generation
is preserved and reported as an explicit conflict; a live prior generation
still fails closed. Real reinstall proof remains in progress.

## Approach

After a successful Windows stop and idle-state proof, poll only for the captured
prior runtime generation to become unreachable and disappear. Reuse the
authenticated descriptor fingerprint and exact-owner cleanup boundary. Bound
the wait and preserve fail-closed rollback when the prior generation remains
live or an unexpected replacement appears.

## Dependencies

AR-13 owns the optional service lifecycle. AR-98 owns truthful manifest
inspection. ADR-0031 and ADR-0051 require a durable user service and
identity-stable runtime publication. This correction can be verified
independently.

## Acceptance

- [x] Install, restart, and stop wait a bounded time for the exact prior runtime generation to clear.
- [x] Replacement generations remain protected and cannot be mistaken for stale state.
- [x] A genuinely live old runtime still fails closed and rolls back.
- [ ] Focused simulated regressions and the real Windows reinstall pass.
- [ ] The full suite and hosted Windows/Linux gates pass.
