---
title: "AR-62: Tolerate identity-stable SQLite sidecar trust races"
status: done
category: roadmap
created: 2026-07-16
updated: 2026-07-16
tags: [operations, sqlite, concurrency, security, testing]
related:
  - docs/decisions/0012-canonical-sqlite-audit-store.md
  - docs/decisions/0052-require-trusted-parents-for-sqlite-store-paths.md
  - docs/roadmap/issue-AR-22-concurrent-storage-acl-repair.md
  - docs/roadmap/issue-AR-56-require-trusted-parents-for-sqlite-store-paths.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: operations
issue_id: AR-62
priority: p0
tracker_url: "https://github.com/Holeshot-Software-LLC/agency-runtime/issues/63"
depends_on: [AR-22, AR-56]
blocks: []
---

# AR-62: Tolerate identity-stable SQLite sidecar trust races

## Problem

Concurrent Store initialization can observe a SQLite WAL or shared-memory
sidecar while another connection is opening or closing that same file. On
Windows, the security-descriptor read can fail briefly even though the file is
inside the trusted Store namespace. Treating that transient probe exactly like
a stable broad ACL makes otherwise safe concurrent schema migration fail.

## Current state

The repair path captures the sidecar's device and inode before its trust probe.
If the first probe fails, optional sidecars are re-inspected: disappearance or
replacement is handled as bounded SQLite churn, while an unchanged identity
gets one trust recheck. A stable identity that remains unsafe still fails
closed. The primary database and storage directories never receive this
optional-sidecar allowance.

## Approach

Keep the existing process-wide permission-repair lock and identity-safe repair
flow. Move fingerprint capture ahead of the initial trust probe, reuse the
existing optional-sidecar identity comparison, and allow only one stable
recheck. Exercise concurrent legacy-store initialization repeatedly and cover
disappearance, replacement, transient denial, and persistently unsafe ACLs.

## Dependencies

AR-22 serialized storage ACL repair, while AR-56 established the trusted-parent
and single-link Store boundary. This item preserves both controls and narrows
only the handling of ephemeral SQLite-owned sidecars.

## Acceptance

- [x] Optional sidecars are fingerprinted before an initial trust failure is classified.
- [x] Disappearing or replaced optional sidecars retry through bounded identity checks.
- [x] An unchanged sidecar receives at most one stable trust recheck.
- [x] A persistently unsafe sidecar, primary database, or directory still fails closed.
- [x] Repeated concurrent legacy Store migration is serialized and idempotent on Windows.
- [x] Exact line and branch coverage plus the full security, performance, and portability gates pass.
