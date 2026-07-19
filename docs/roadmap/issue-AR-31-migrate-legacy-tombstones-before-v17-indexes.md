---
title: "AR-31: Migrate legacy tombstones before v17 indexes"
status: done
category: roadmap
created: 2026-07-15
updated: 2026-07-15
tags: [storage, migration, integrity, testing, bug]
related:
  - docs/decisions/0048-preserve-legacy-tombstones-without-inventing-session-identity.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: operations
issue_id: AR-31
priority: p0
tracker_url: "https://github.com/Holeshot-Software-LLC/agency-runtime/issues/32"
depends_on: []
blocks:
  - AR-55
  - AR-90
---

# AR-31: Migrate legacy tombstones before v17 indexes

## Problem

Installing schema v17 over an existing schema-v16 Agency database failed before
host wiring with `sqlite3.OperationalError: no such column: session_digest`.
The base schema attempted to create the new tombstone session/sequence index
before the legacy table had those columns.

## Current state

The defect reproduced on the real Windows profile and on a read-only backup
containing 103 existing runs. Empty-database and artifact smoke tests did not
exercise this upgrade path, so every clean-install gate passed while the durable
profile upgrade remained broken.

## Approach

Move the v17 index out of the base schema transaction, add the legacy columns
first, preserve every trace tombstone, and assign the domain-separated
uncorrelated-session digest where v16 retained no recoverable session identity.
Allocate positive monotonic tombstone sequences above existing evidence,
validate the entire barrier, and only then create the index. Cover both empty
and populated v16 databases and prove the migration against a copy of the real
profile before retrying installation. Seal the strengthened key, digest,
counter, and global-sequence invariants as schema v18 so a store touched by the
earlier v17 candidate receives the complete repair.

## Dependencies

This defect was discovered while installing the completed AR-25 through AR-30
candidate. It blocks the reviewed Codex installation and final merge.

## Acceptance

- [x] Existing schema-v16 databases upgrade atomically through v17 into v18.
- [x] Candidate schema-v17 databases receive the complete v18 integrity repair.
- [x] Legacy trace tombstones are preserved without inventing original session identity.
- [x] Tombstone digests, sequences, counter, and index pass schema-v18 integrity checks.
- [x] Empty and populated legacy databases have warning-strict regression coverage.
- [x] The reviewed artifact installs into the real Codex profile and passes smoke.
- [x] Full Windows/Linux exact coverage, packaging, CI, merge, and tracker reconciliation pass.
