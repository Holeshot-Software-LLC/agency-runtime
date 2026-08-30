---
title: "Preserve legacy tombstones without inventing session identity"
status: accepted
category: decisions
created: 2026-07-15
updated: 2026-07-15
tags: [architecture, storage, migration, privacy, integrity]
related:
  - docs/roadmap/issue-AR-31-migrate-legacy-tombstones-before-v17-indexes.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
id: ADR-0048
type: decision
deciders: [maintainers]
---

# ADR-0048: Preserve legacy tombstones without inventing session identity

## Context

Schema v16 trace tombstones retained a trace HMAC and retirement time but no
session identity or monotonic turn sequence. Schema v17 needs both values to
prevent terminal-correlation resurrection across retained session history. A
legacy database cannot reconstruct a session that was deliberately not stored.
Creating the v17 index before adding and backfilling those columns also makes a
normal in-place upgrade fail.

## Decision

Upgrade the table before creating any index that references v17 columns.
Preserve every existing trace HMAC and retirement time. Represent the unknown
legacy session with the same domain-separated HMAC used for an uncorrelated
session; never infer or fabricate an original session ID. Allocate each pending
tombstone a deterministic positive sequence above all valid live and retired
sequences, validate the complete barrier, advance the durable counter, and only
then create the session/sequence indexes. Commit the strengthened key, digest,
counter, and global-sequence invariant as schema v18 so databases touched by the
earlier v17 candidate cannot retain an incomplete same-version contract.

## Consequences

- Legacy trace-level anti-resurrection evidence remains intact.
- Named sessions are not falsely associated with anonymous historical records.
- Uncorrelated recovery fails conservatively across legacy retirement barriers.
- Migration is transactional, deterministic, and safe to retry.
- Populated legacy-schema fixtures become a mandatory release gate.

## Alternatives

- Drop legacy tombstones. Rejected because it would reopen retired trace IDs.
- Reconstruct a session from other tables. Rejected because the association was
  intentionally not retained and any reconstruction could be false.
- Use a plain sentinel string. Rejected because tombstone identity remains
  content-free and domain-separated through the store-local HMAC contract.
- Mark the new index optional. Rejected because that would leave upgraded stores
  with inconsistent integrity and query behavior.
