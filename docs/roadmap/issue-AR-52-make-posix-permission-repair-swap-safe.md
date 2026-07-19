---
title: "AR-52: Make POSIX permission repair swap-safe"
status: done
category: roadmap
created: 2026-07-15
updated: 2026-07-15
tags: [security, posix, filesystem, permissions, race-condition]
related:
  - docs/decisions/0012-canonical-sqlite-audit-store.md
  - docs/THREAT_MODEL.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: operations
issue_id: AR-52
priority: p0
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/53
depends_on:
  - AR-39
blocks:
  - AR-54
  - AR-56
---

# AR-52: Make POSIX permission repair swap-safe

## Problem

POSIX permission hardening validates a path with `lstat` and then calls a
path-based `chmod`. A concurrent final-component swap can redirect that
mutation to an unintended user-owned target before the subsequent identity
check detects the race.

## Current state

Store and configuration paths reject links and reparse points before and after
permission repair, and Windows uses a separate ACL boundary. The POSIX mutation
itself is not yet bound to the exact filesystem object that was validated.

## Approach

Open the intended regular file or directory without following the final link,
verify its descriptor identity and kind, apply permissions with `fchmod`, and
revalidate identity before accepting success. Reuse the bounded primitive for
Store, configuration, and dashboard-owned directory repair without changing
Windows ACL semantics.

## Dependencies

AR-39 establishes fail-closed storage/configuration identity. This item closes
the remaining time-of-check/time-of-use gap in its POSIX permission mutation.

## Acceptance

- [x] POSIX permission changes are applied through a validated descriptor.
- [x] Final-component link swaps cannot redirect `chmod` to another target.
- [x] Wrong-kind, replaced, and inaccessible identities fail closed.
- [x] Windows ACL behavior and supported POSIX file/directory behavior remain compatible.
- [x] Full exact-coverage, Linux/Windows, security, and tracker gates pass.
