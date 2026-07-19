---
title: "AR-98: Validate launcher identity in dashboard service status"
status: in_progress
category: roadmap
created: 2026-07-18
updated: 2026-07-18
tags: [dashboard, service, installer, diagnostics]
related:
  - docs/roadmap/issue-AR-13-optional-dashboard-service-configuration.md
  - docs/roadmap/issue-AR-38-dashboard-service-environment-durability.md
  - docs/decisions/0029-secure-local-dashboard-and-bounded-observability.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: dashboard
issue_id: AR-98
priority: p1
tracker_url: "https://github.com/Holeshot-Software-LLC/agency-runtime/issues/99"
depends_on: []
blocks: []
---

# AR-98: Validate launcher identity in dashboard service status

## Problem

The read-only dashboard service status and open-recovery paths skipped launcher
artifact validation. A healthy schema-v2 service could therefore report
`manifest_current: false` and `repair_recommended: true` even while its
registered definition and running process were current.

## Current state

The installed Windows artifact reproduced the contradictory signal. Calling the
same inspector with launcher validation enabled returned the truthful current
state without mutating the service. The focused correction and installed
artifact regression are in progress.

## Approach

Use the existing bounded, read-only launcher identity validation in both service
status and open-recovery inspection. Preserve the current token-redaction and
mutation-free status contract; do not repair, restart, or rewrite the service
merely to determine whether its manifest is current.

## Dependencies

AR-13 owns the optional service lifecycle and AR-38 owns durable service
environment identity, but this correction can be verified independently.
ADR-0029 owns the secure, truthful local dashboard boundary.

## Acceptance

- [ ] Service status validates the installed launcher identity without mutation.
- [ ] Open recovery uses the same current-manifest evidence.
- [ ] A healthy service reports `manifest_current: true` and
      `repair_recommended: false`.
- [ ] Regression tests cover both read-only paths and preserve token redaction.
- [ ] The rebuilt installed Windows artifact and live dashboard service pass.
