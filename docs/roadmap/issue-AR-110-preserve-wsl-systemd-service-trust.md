---
title: "AR-110: Preserve dashboard service trust under WSL systemd namespace remapping"
status: done
category: roadmap
created: 2026-07-20
updated: 2026-07-20
tags: [dashboard, systemd, wsl, linux, security, portability]
related:
  - docs/roadmap/issue-AR-13-optional-dashboard-service-configuration.md
  - docs/roadmap/issue-AR-66-bind-systemd-unit-to-trusted-xdg-namespace.md
  - docs/decisions/0031-optional-user-dashboard-service-and-shared-configuration.md
  - docs/decisions/0075-preserve-config-trust-under-wsl-systemd.md
  - docs/THREAT_MODEL.md
  - docs/TROUBLESHOOTING.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: operations
issue_id: AR-110
priority: p0
tracker_url: "https://github.com/Holeshot-Software-LLC/agency-runtime/issues/113"
depends_on: []
blocks: []
---

# AR-110: Preserve dashboard service trust under WSL systemd namespace remapping

## Problem

WSL's systemd user manager applies `PrivateTmp=true` through a mount namespace
that can expose root-owned ancestors as overflow UID `65534`. The dashboard
worker then correctly rejects its otherwise owner-private configuration path as
permitting cross-account substitution. Service installation therefore rolls
back even though the same exact installed worker starts successfully outside
that namespace.

## Current state

The exact merge wheel installs on native WSL and creates its private runtime
state, but `agency dashboard service install` cannot reach readiness. Binary
isolation proved that `NoNewPrivileges`, `UMask`, and restricted address
families remain compatible; `PrivateTmp` alone causes the namespace identity
distortion. Normal Linux systemd service generation remains unaffected.

## Approach

Detect WSL positively from bounded Linux kernel evidence while generating the
user unit. Retain `PrivateTmp=true` on normal Linux and on every unknown or
unreadable environment. Omit only that directive on positively identified WSL,
while retaining owner-private runtime/configuration directories,
`NoNewPrivileges`, `UMask=0077`, and the address-family restriction. Do not
weaken the shared configuration namespace predicate.

## Dependencies

AR-13 defines the optional user service. AR-66 and ADR-0031 define the trusted
XDG namespace and fail-closed service boundary.

## Acceptance

- [x] Normal Linux units retain `PrivateTmp=true`.
- [x] Positively identified WSL units omit only `PrivateTmp`.
- [x] Missing or unreadable kernel evidence fails secure and retains `PrivateTmp`.
- [x] Configuration namespace trust remains unchanged and fail-closed.
- [x] Focused service and security tests pass with exact line and branch coverage.
- [x] An exact built wheel installs, starts, reports healthy, and uninstalls through real WSL `systemd --user`.
- [x] Documentation, worklog, and tracker mapping remain synchronized.

The exact committed wheel passed install, start, healthy-status, stop, and
uninstall against real WSL `systemd --user`. PR #114 then passed the complete
hosted Windows/Linux matrix and merged the policy unchanged.
