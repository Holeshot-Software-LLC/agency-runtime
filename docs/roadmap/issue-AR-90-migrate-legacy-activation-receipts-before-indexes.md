---
title: "AR-90: Migrate legacy activation receipts before current indexes"
status: in_progress
category: roadmap
created: 2026-07-18
updated: 2026-07-18
tags: [storage, migration, activation, integrity, bug]
related:
  - docs/roadmap/issue-AR-31-migrate-legacy-tombstones-before-v17-indexes.md
  - docs/roadmap/issue-AR-79-installed-isolated-header-proof.md
  - docs/decisions/0012-canonical-sqlite-audit-store.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: operations
issue_id: AR-90
priority: p0
tracker_url: "https://github.com/Holeshot-Software-LLC/agency-runtime/issues/91"
depends_on: [AR-31]
blocks: [AR-79]
---

# AR-90: Migrate legacy activation receipts before current indexes

## Problem

A durable Agency Runtime installation created under schema v19 can contain a
`delegation_activation_receipts` table without the later `grant_id` column.
Current startup executed `idx_activation_grants_public_id` before legacy
migration added or rebuilt that column, so Store initialization failed with
`no such column: grant_id`. A later remediation-provenance index exposed the
same ordering class for `agent_import_events.event_sequence` on the real durable
profile. Both defects block an otherwise valid in-place upgrade before routing,
dashboard, or header finalization can start.

## Current state

Every index that depends on a migrated column now runs only after its owning
table has been normalized. A populated real-shape v19 activation regression
proves row preservation, safe grant defaults, repeated-open idempotency, and
mid-migration rollback. An exact pre-v31 import-event regression proves
deterministic sequence backfill and canonical index validation; the real durable
profile now upgrades and starts the dashboard successfully. The reviewed wheel
previously upgraded the activation shape, and a fresh isolated Codex canary
emitted a valid exact six-line header with one correlated routing row, two
finalization rows, and a persisted attestation. The final repository-wide
release gates remain in progress.

## Approach

Normalize or rebuild each legacy table before creating any index that depends
on current columns. Keep migration transactional, idempotent, rollback-safe,
and data-preserving. Add exact v19 activation and pre-v31 import-event
regressions plus clean-database and repeated-open coverage, then reinstall the
reviewed artifact and rerun the installed Codex routing and header canary.

## Dependencies

AR-31 establishes the legacy-before-index migration pattern. This defect blocks
AR-79's installed Codex proof until the durable profile can open safely.

## Acceptance

- [x] A real-shape v19 database opens and migrates to the current schema.
- [x] No index is created before every referenced column exists.
- [x] Existing legacy activation evidence is preserved under the current bounded contract.
- [x] A failed migration rolls back cleanly and a repeated open is idempotent.
- [x] New-database initialization remains unchanged and fully covered.
- [x] Legacy import events receive deterministic positive sequences before provenance indexes run.
- [x] The real durable profile upgrades and starts the dashboard without an index-order failure.
- [x] The refreshed installed Codex canary emits the exact six-line current-turn header with correlated routing and finalization evidence.
- [ ] Full coverage, documentation, packaging, and Windows/Linux gates pass.
