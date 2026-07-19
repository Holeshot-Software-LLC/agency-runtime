---
title: "AR-66: Bind the systemd unit to a trusted XDG namespace"
status: done
category: roadmap
created: 2026-07-16
updated: 2026-07-16
tags: [security, dashboard, systemd, xdg, filesystem, race-condition]
related:
  - docs/decisions/0031-optional-user-dashboard-service-and-shared-configuration.md
  - docs/decisions/0051-bind-dashboard-runtime-publication-to-validated-filesystem-identities.md
  - docs/roadmap/issue-AR-54-make-dashboard-runtime-publication-swap-safe.md
  - docs/THREAT_MODEL.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: security
issue_id: AR-66
priority: p0
tracker_url: "https://github.com/Holeshot-Software-LLC/agency-runtime/issues/67"
depends_on: [AR-54]
blocks: []
---

# AR-66: Bind the systemd unit to a trusted XDG namespace

## Problem

Linux service context accepts any absolute `XDG_CONFIG_HOME`, but systemd unit
writes and rollback previously validated only the final parent. A
cross-account-writable ancestor or swapped parent could redirect or replace the
owned unit across read, write, removal, or rollback.

## Current state

The XDG root is now an explicit frozen context identity. Planning, inspection,
install, unlink, and rollback validate its real mutation-safe ancestor chain;
missing descendants are created through the same private-directory primitive
used by other sensitive runtime state.

## Approach

Reject unsafe absolute XDG roots instead of silently falling back. Create
missing descendants only below a proven owner-safe boundary, pass the trusted
root through atomic write and restore helpers, and revalidate the namespace and
unit identity before each mutation and rollback step.

## Dependencies

ADR-0031 defines user-scoped systemd registration and AR-54/ADR-0051 define
swap-safe dashboard filesystem publication. This item extends those controls to
the configured Linux unit namespace.

## Acceptance

- [x] Cross-account-writable XDG ancestors fail before any unit mutation.
- [x] Link, replacement, and identity changes in the unit parent fail closed.
- [x] Safe absolute XDG roots and the default home-relative root remain supported.
- [x] Atomic write, read, unlink, and rollback share one trusted-root contract.
- [x] Failure never falls back to a different service registration path.
- [x] Linux portability, transaction, full-suite, exact-coverage, and installed service gates pass.
