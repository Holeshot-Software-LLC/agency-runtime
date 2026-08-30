---
title: "AR-41: Close store connections after maintenance repair failure"
status: done
category: roadmap
created: 2026-07-15
updated: 2026-07-15
tags: [sqlite, reliability, resources, operations]
related:
  - docs/decisions/0012-canonical-sqlite-audit-store.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: operations
issue_id: AR-41
priority: p0
tracker_url: "https://github.com/Holeshot-Software-LLC/agency-runtime/issues/42"
depends_on: []
blocks: []
---

# AR-41: Close store connections after maintenance repair failure

## Problem

Store maintenance repairs file permissions before closing its SQLite connection.
If the repair raises, connection cleanup is skipped, which can retain WAL locks
and cascade into dashboard or runtime failures.

## Current state

The connection close and permission repair share one `finally` block without a
nested cleanup guarantee. The primary operation is exception-safe, but its
resource release is not.

## Approach

Make connection closure unconditional even when permission repair fails. Retain
the original repair error while proving the connection is closed exactly once.

## Dependencies

None. This strengthens the canonical SQLite store contract in ADR-0012.

## Acceptance

- [x] A permission-repair failure cannot skip connection closure.
- [x] A regression test observes cleanup under the injected failure.
- [x] Normal maintenance behavior and original error propagation remain intact.
- [x] Full exact-coverage, Windows/Linux, package, and tracker gates pass.
