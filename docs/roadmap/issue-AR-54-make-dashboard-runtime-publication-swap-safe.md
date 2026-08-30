---
title: "AR-54: Make dashboard runtime publication swap-safe"
status: done
category: roadmap
created: 2026-07-15
updated: 2026-07-16
tags: [security, dashboard, posix, filesystem, race-condition]
related:
  - docs/decisions/0029-secure-local-dashboard-and-bounded-observability.md
  - docs/decisions/0051-bind-dashboard-runtime-publication-to-validated-filesystem-identities.md
  - docs/roadmap/issue-AR-66-bind-systemd-unit-to-trusted-xdg-namespace.md
  - docs/THREAT_MODEL.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: operations
issue_id: AR-54
priority: p0
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/55
depends_on:
  - AR-52
blocks: [AR-66]
---

# AR-54: Make dashboard runtime publication swap-safe

## Problem

The local dashboard runtime lock and bearer descriptor publication use
path-based permission repair and path opens that can follow or race a
substituted link. On POSIX, an actor able to modify a writable runtime path
could redirect mutation or descriptor publication to an unintended filesystem
object.

## Current state

General Store, configuration, and dashboard-directory permission repair is
descriptor-bound under AR-52. The dashboard runtime publisher still has its own
path-based lock and publication sequence that does not reuse the hardened
identity boundary.

## Approach

Open and lock the exact runtime lock file without following links, validate its
descriptor kind and identity before and after mutation, and repair the runtime
directory through the fd-safe bounded primitive. Publish the bearer descriptor
only after confirming the same validated directory identity, and fail closed on
links, wrong kinds, or substitution.

## Dependencies

AR-52 provides the descriptor-safe POSIX permission primitive. ADR-0029 defines
the local authenticated dashboard boundary that this publication path must
preserve.

## Acceptance

- [x] The runtime lock is opened without following the final path component.
- [x] Lock and directory identity, kind, and ownership changes fail closed.
- [x] Permission mutation and descriptor publication cannot be redirected by a link or swap.
- [x] Failure diagnostics do not expose bearer material or sensitive paths.
- [x] Supported Windows behavior remains compatible.
- [x] Exact-coverage, Linux/Windows, security, and tracker gates pass.
