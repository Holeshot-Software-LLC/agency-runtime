---
title: "AR-98: Validate launcher identity in dashboard service status"
status: done
category: roadmap
created: 2026-07-18
updated: 2026-07-19
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

The installed Windows artifact reproduced the contradictory signal. The
corrected inspector now validates launcher identity on both read-only paths.
The rebuilt installed service reports a current owned manifest, no definition
drift, no repair recommendation, and remains active and reachable.

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

- [x] Service status validates the installed launcher identity without mutation.
- [x] Open recovery uses the same current-manifest evidence.
- [x] A healthy service reports `manifest_current: true` and
      `repair_recommended: false`.
- [x] Regression tests cover both read-only paths and preserve token redaction.
- [x] The rebuilt installed Windows artifact and live dashboard service pass.
