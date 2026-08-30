---
title: "AR-133: Make finalization evidence atomic, complete, and bounded"
status: done
category: roadmap
created: 2026-07-26
updated: 2026-08-12
tags: [evidence, sqlite, http, mcp, transactions]
related:
  - docs/THREAT_MODEL.md
  - docs/decisions/0093-atomic-finalization-evidence-batches.md
  - agency_runtime/server/http.py
  - agency_runtime/core/store
supersedes: []
superseded_by: null
type: issue
epic: observability
issue_id: AR-133
priority: p0
tracker_url: null
depends_on: []
blocks: []
---

# AR-133: Make finalization evidence atomic, complete, and bounded

## Problem

One finalization request can perform hundreds of independent Store connections
and commits. A later duplicate or conflicting lineage failure leaves earlier
records committed, while some execution identity fields are coerced rather
than type-validated at the boundary.

## Current state

The individual Store methods are bounded and parameterized, but request-level
atomicity is absent. Malformed `executed_worker_kind`, `executed_worker_id`, or
`native_run_id` values can become generic server failures instead of a clean
client rejection. MCP also accepts caller-supplied host/model attribution that
is not authoritative evidence.

## Approach

Validate the complete bounded batch before opening one `BEGIN IMMEDIATE`
transaction, insert every evidence record through transaction-scoped helpers,
then finalize or roll back as one unit. Reject unknown fields, duplicate keys,
conflicting lineage, wrong types, oversized identifiers, and caller-spoofed
host/model attribution before mutation.

## Dependencies

ADR-0093 defines the transaction boundary. AR-130 retains authoritative trust
checks at connection entry.

## Acceptance

- [x] A failed finalization request persists no partial evidence.
- [x] Valid maximum-size batches use one connection and one transaction.
- [x] All execution identity fields are strictly typed and bounded.
- [x] Host and actual model derive from installed context and durable receipts.
- [x] Replay, conflict, interruption, and concurrent-finalization tests pass.
- [x] HTTP and MCP return stable sanitized client errors for invalid batches.

## Implementation evidence

Finalization now validates the entire bounded request before opening one
BEGIN IMMEDIATE transaction, writes every evidence row and the final receipt
through transaction-scoped helpers, and rolls the complete batch back on
conflict, replay, interruption, or invalid lineage. Execution identities are
strict strings with canonical bounds, caller-supplied host/model attribution
is absent, and HTTP/MCP return typed sanitized failures. The focused atomic
batch suite passed 21 tests with 2 skips; the integrated
transaction/observability/MCP/HTTP slice passed 147 tests with 8 skips.
All acceptance criteria are satisfied locally; tracker creation and
synchronization remain pending explicit outward-write authorization.
