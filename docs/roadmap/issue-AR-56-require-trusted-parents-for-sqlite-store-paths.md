---
title: "AR-56: Require trusted parents for SQLite Store paths"
status: done
category: roadmap
created: 2026-07-15
updated: 2026-07-16
tags: [sqlite, security, filesystem, permissions, race-condition]
related:
  - docs/decisions/0012-canonical-sqlite-audit-store.md
  - docs/decisions/0052-require-trusted-parents-for-sqlite-store-paths.md
  - docs/THREAT_MODEL.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: operations
issue_id: AR-56
priority: p0
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/57
depends_on:
  - AR-39
  - AR-52
blocks: [AR-61, AR-62]
---

# AR-56: Require trusted parents for SQLite Store paths

## Problem

An explicit SQLite database path can live in a pre-existing shared-writable
parent that Agency does not harden. Path checks followed by `sqlite3.connect`
then leave a cross-account substitution window, and read-only schema inspection
also dereferences the checked path before opening it.

## Current state

The default Store directory is created owner-private, and links, reparse points,
wrong kinds, and unsafe final-component permission mutation are rejected. A
caller-supplied parent, however, is intentionally not mutated and is not yet
required to provide the equivalent private ownership boundary.

## Approach

Require every explicit Store parent to be non-link and owned/private enough to
exclude cross-account substitution, failing closed instead of rewriting an
arbitrary shared directory. Preserve owner-private default directory creation,
remove avoidable path dereference from schema inspection, and compare stable
database identity around SQLite opens where the platform exposes it.

## Dependencies

AR-39 makes configured storage identity fail closed, and AR-52 provides
descriptor-safe permission repair. ADR-0012 remains the canonical Store
contract; ADR-0052 defines the explicit-parent trust boundary.

## Acceptance

- [x] Shared/group/world-writable explicit parents are rejected before database mutation on POSIX.
- [x] Windows enforces the equivalent current-user-private ACL boundary.
- [x] Safe explicit and default Store paths remain portable and idempotent.
- [x] SQLite opens do not introduce avoidable path dereference.
- [x] Same-account substitution is documented as inside the accepted local-user boundary.
- [x] Exact-coverage, migration, Linux/Windows security, and tracker gates pass.
