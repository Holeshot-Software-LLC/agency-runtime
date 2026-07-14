---
title: "AR-22: Serialize concurrent Windows storage ACL repair"
status: done
category: roadmap
created: 2026-07-13
updated: 2026-07-14
tags: [windows, sqlite, security, concurrency, reliability]
related:
  - docs/decisions/0012-canonical-sqlite-audit-store.md
  - docs/decisions/0039-fail-before-dacl-mutation-under-restricted-windows-tokens.md
  - docs/roadmap/issue-AR-17-production-hardening-portability.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: operations
issue_id: AR-22
priority: p0
tracker_url: "https://github.com/Holeshot-Software-LLC/agency-runtime/issues/23"
depends_on: []
blocks: [AR-17]
---

# AR-22: Serialize concurrent Windows storage ACL repair

## Problem

Concurrent Store instances can inspect and mutate the same SQLite WAL or SHM
sidecar ACL at the same time on Windows. Their instance-local permission
fingerprints do not protect the shared filesystem target. A transient sidecar
replacement or overlapping DACL operation can therefore reject valid
initialization even when the final object is private.

## Current state

Hosted Python 3.14 exposed the race in the concurrent legacy-store migration
stress test while enforcing the private ACL on a shared database SHM sidecar.
The storage code already rejects links, reparse points, non-regular targets,
and stable insecure permissions, but its inspect, mutate, and postcheck sequence
was not serialized across Store instances in one process.

## Approach

Protect storage creation and each ACL inspect, apply, and postcheck critical
section with one process-wide reentrant lock. If permission repair for an
optional WAL or SHM target fails, read its metadata again. Retry only when that
fresh observation proves disappearance or a changed device and inode identity.
Continue to reject stable failures and any replacement link or reparse point.

## Dependencies

This applies ADR-0012's shared SQLite evidence boundary and ADR-0039's
fail-before-mutation owner-private storage rule without weakening either
postcondition. Both hosted Windows endpoints passed with the serialized repair.

## Acceptance

- [x] ACL repair for a shared target is serialized across Store instances.
- [x] Optional sidecar disappearance and proven identity change retry safely.
- [x] Stable ACL failures remain fatal.
- [x] Replacement links and reparse points remain fatal.
- [x] Deterministic concurrency and identity-race regressions pass.
- [x] The original native Windows concurrent migration stress passes repeatedly.
- [x] Hosted Windows Python 3.10 and 3.14 suites pass.
- [x] Exact coverage, review, merge, and tracker closure pass.
