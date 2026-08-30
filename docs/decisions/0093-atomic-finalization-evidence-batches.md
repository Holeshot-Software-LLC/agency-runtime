---
title: "Commit one finalization evidence batch atomically"
status: accepted
category: decisions
created: 2026-07-26
updated: 2026-07-26
tags: [evidence, sqlite, transactions, finalization]
related:
  - docs/roadmap/issue-AR-133-atomic-finalization-evidence.md
  - docs/decisions/0012-canonical-sqlite-audit-store.md
  - docs/decisions/0027-authoritative-runtime-evidence-traces.md
supersedes: []
superseded_by: null
id: ADR-0093
type: decision
deciders: [maintainers]
---

# ADR-0093: Commit one finalization evidence batch atomically

## Context

Finalization is one authority decision but currently expands into many
independent Store calls. If record 200 conflicts after records 1-199 commit, the
request fails while the Store contains a partial account of work. Reopening
connections also repeats trust, setup, and lock overhead.

## Decision

The complete finalization envelope is schema-validated and semantically checked
before mutation. One Store method opens one trusted connection, starts
`BEGIN IMMEDIATE`, records every bounded evidence item through
transaction-scoped helpers, performs terminal validation, and commits once.
Any validation, conflict, interruption, or persistence failure rolls back the
entire batch.

Authoritative host/model attribution is derived from installed context and
durable provider receipts, not caller labels.

## Consequences

- A successful terminal receipt corresponds to one complete durable batch.
- Conflicts no longer leave request-local partial evidence.
- Connection/trust overhead falls without weakening authorization checks.
- Large callers must fit explicit item, byte, identifier, and time limits.

## Alternatives

- **Compensating deletes after failure.** Rejected because audit evidence and
  concurrent readers make compensation ambiguous.
- **One transaction per evidence type.** Rejected because cross-type atomicity
  is the required property.
- **Retain partial progress and return details.** Rejected because a failed
  finalization cannot authoritatively claim a coherent subset.
