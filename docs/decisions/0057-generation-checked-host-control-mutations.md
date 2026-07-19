---
title: "Require generation-checked atomic host-control mutations"
status: accepted
category: decisions
created: 2026-07-16
updated: 2026-07-16
tags: [operations, concurrency, sqlite, host-controls, dashboard, mcp]
related:
  - docs/roadmap/issue-AR-70-generation-check-host-controls.md
  - docs/roadmap/issue-AR-77-validate-brokered-control-transition-receipts.md
  - docs/decisions/0034-persistent-soft-host-control.md
  - docs/decisions/0053-durable-fail-enabled-master-control.md
  - docs/THREAT_MODEL.md
  - docs/TROUBLESHOOTING.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
id: ADR-0057
type: decision
deciders: [maintainers]
---

# ADR-0057: Require generation-checked atomic host-control mutations

## Context

ADR-0034 makes SQLite the durable source of truth for each host integration's
immediate soft control. Persistence alone does not prevent a lost update:
several dashboard tabs, CLI processes, MCP clients, or host commands can read
one value and then publish conflicting choices in an order the operator did
not intend. A last-writer-wins toggle also differs from the generation-checked
Agency-wide master control and makes the dashboard appear safer than it is.

## Decision

Add a non-negative monotonic generation to each canonical `host_controls`
row. Treat an absent legacy row as enabled at generation zero. Every public
mutation must carry the exact generation observed by its caller, or an
in-process convenience surface must read that generation immediately before
attempting the same compare-and-swap operation.

Acquire an immediate SQLite write transaction, read the current row, compare
its generation with the expected value, and publish within that transaction.
A real enabled-state transition increments the generation exactly once. An
idempotent request returns the committed row without changing its generation,
timestamp, or source. Reject stale generations and counter exhaustion; never
wrap, silently retry a stale external choice, or split verification into a
second read transaction.

Project the committed generation through CLI, dashboard, MCP, and generated
host status. The authenticated dashboard maps a stale mutation to HTTP 409 so
the client refreshes before an operator deliberately retries. The MCP control
tool requires `expected_generation`. Multi-host CLI operations retain every
per-host result and return failure if any compare-and-swap fails.

This decision extends rather than supersedes ADR-0034. The separate pre-Store
Agency-wide master document and its generation remain governed by ADR-0053.

## Consequences

- Concurrent operators cannot unknowingly overwrite a newer host-control
  choice.
- Status responses become the capability needed for a later mutation.
- Idempotent writes remain cheap and do not create artificial conflicts.
- Schema migration preserves legacy state while making subsequent transitions
  monotonic and auditable.
- Clients must handle an explicit stale-generation result by refreshing and
  asking the operator to retry deliberately.

## Alternatives

- Keep last-writer-wins updates. Rejected because concurrent choices become
  indistinguishable from intentional replacement.
- Retry automatically after a conflict. Rejected because that would overwrite
  the newer operator choice with stale intent.
- Reuse the global master generation. Rejected because host soft controls live
  in SQLite, have independent scopes, and may change without the master state.
- Increment on every request, including no-ops. Rejected because it creates
  needless conflicts without representing a state transition.
