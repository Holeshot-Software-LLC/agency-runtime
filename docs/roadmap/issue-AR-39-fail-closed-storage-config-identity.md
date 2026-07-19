---
title: "AR-39: Fail closed when configured storage identity is unreadable"
status: done
category: roadmap
created: 2026-07-15
updated: 2026-07-15
tags: [storage, configuration, fail-closed, correlation, security]
related:
  - docs/decisions/0006-config-first-redacted-configuration.md
  - docs/decisions/0012-canonical-sqlite-audit-store.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: operations
issue_id: AR-39
priority: p0
tracker_url: "https://github.com/Holeshot-Software-LLC/agency-runtime/issues/40"
depends_on:
  - AR-36
blocks:
  - AR-56
  - AR-52
  - AR-44
  - AR-48
---

# AR-39: Fail closed when configured storage identity is unreadable

## Problem

Default database resolution catches every configuration failure and silently
opens the conventional database. A malformed or unreadable configured file can
therefore split turn and receipt state across two databases instead of failing
closed.

## Current state

Explicit `Store(db_path)` construction is deterministic, but default Store
construction treats configuration validation, permission, and internal errors
as permission to select another state file. The fallback undermines durable
turn correlation and can make evidence appear missing.

## Approach

Make typed configuration the sole authority for default database resolution and
propagate validation or read failures. Keep explicit database construction for
controlled recovery and tests. Cover malformed and unreadable config identities
without creating or opening the fallback database.

## Dependencies

AR-36 defines stable config-relative path semantics. This correction enforces
ADR-0006 and ADR-0012 when that configuration cannot be trusted.

## Acceptance

- [x] Invalid or unreadable configured identity cannot open a fallback database.
- [x] Environment and config-relative database paths retain documented precedence.
- [x] Default Store construction introduces no bootstrap/import-cycle regression.
- [x] Full exact-coverage, Windows/Linux, package, and tracker gates pass.
