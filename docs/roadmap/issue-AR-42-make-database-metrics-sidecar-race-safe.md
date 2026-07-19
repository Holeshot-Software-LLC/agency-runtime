---
title: "AR-42: Make database metrics resilient to disappearing sidecars"
status: done
category: roadmap
created: 2026-07-15
updated: 2026-07-15
tags: [sqlite, dashboard, concurrency, observability]
related:
  - docs/decisions/0012-canonical-sqlite-audit-store.md
  - docs/decisions/0029-secure-local-dashboard-and-bounded-observability.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: operations
issue_id: AR-42
priority: p0
tracker_url: "https://github.com/Holeshot-Software-LLC/agency-runtime/issues/43"
depends_on: []
blocks: []
---

# AR-42: Make database metrics resilient to disappearing sidecars

## Problem

The live dashboard checks whether SQLite WAL and SHM sidecars exist and then
stats them. SQLite may remove a sidecar between those operations, producing an
intermittent metrics exception and an HTTP 500 from `/api/live`.

## Current state

`database_sizes()` has a check-then-act race for transient sidecars. Its link
safety validation is required, but disappearance during the final stat is a
normal concurrent state transition rather than an error.

## Approach

Use one stat attempt per path, preserve link and reparse-point validation, and
treat `FileNotFoundError` as a zero-sized transient sidecar. Exercise the exact
disappearance window deterministically.

## Dependencies

None. This strengthens ADR-0012 storage behavior and ADR-0029 live dashboard
reliability.

## Acceptance

- [x] Sidecar disappearance during metrics collection yields size zero.
- [x] Link and reparse-point rejection remains fail closed.
- [x] A deterministic concurrent-disappearance regression passes.
- [x] Full exact-coverage, Windows/Linux, package, and tracker gates pass.
