---
title: "AR-55: Make SQLite schema-state inspection snapshot-consistent"
status: done
category: roadmap
created: 2026-07-15
updated: 2026-07-15
tags: [sqlite, concurrency, integrity, migration, race-condition]
related:
  - docs/decisions/0012-canonical-sqlite-audit-store.md
  - docs/THREAT_MODEL.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: operations
issue_id: AR-55
priority: p0
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/56
depends_on:
  - AR-31
blocks: []
---

# AR-55: Make SQLite schema-state inspection snapshot-consistent

## Problem

Store schema-state inspection performs related integrity counter and maximum
sequence reads without one explicit read transaction. A concurrent worker
commit can land between those queries, causing a healthy database to be
misclassified as corrupt and blocking startup.

## Current state

SQLite serializes each individual query correctly, but an autocommit reader can
observe a newer committed state on its next query. The integrity relationship
is meaningful only when all of its component reads come from one snapshot.

## Approach

Start an explicit read transaction before evaluating schema objects, version
metadata, counters, and maximum sequences. Complete or roll back that read-only
transaction on every path, and add a deterministic interleaving regression that
coordinates a valid concurrent commit between the formerly separate reads.

## Dependencies

AR-31 establishes the current migration and legacy-state boundary. ADR-0012
requires the SQLite store to remain canonical and fail closed on real integrity
violations.

## Acceptance

- [x] Every related schema-state read observes one SQLite snapshot.
- [x] A concurrent valid receipt commit cannot trigger false corruption.
- [x] Real counter/maximum mismatches still fail closed.
- [x] Read-only inspection rolls back and closes cleanly on success and failure.
- [x] Exact-coverage, spawned-worker, Linux/Windows, and tracker gates pass.
