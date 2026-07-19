---
title: "AR-70: Prevent lost updates in host soft-control mutations"
status: done
category: roadmap
created: 2026-07-16
updated: 2026-07-16
tags: [operations, concurrency, host-controls, cli, dashboard, mcp]
related:
  - docs/decisions/0034-persistent-soft-host-control.md
  - docs/decisions/0057-generation-checked-host-control-mutations.md
  - docs/THREAT_MODEL.md
  - docs/TROUBLESHOOTING.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: operations
issue_id: AR-70
priority: p0
tracker_url: "https://github.com/Holeshot-Software-LLC/agency-runtime/issues/71"
depends_on: []
blocks: [AR-74, AR-77]
---

# AR-70: Prevent lost updates in host soft-control mutations

## Problem

Host-scoped soft controls were durable, but their mutation contract did not
carry a revision. Two dashboard tabs, CLI processes, MCP clients, or host
commands could read the same state and silently overwrite each other. The
global master switch already rejected stale writers, so the weaker host
control path was surprising and unsafe for production operations.

## Current state

Each host-control row now carries a non-negative generation. Every public
mutation supplies the generation it observed, and SQLite compares that value
inside the same immediate write transaction that publishes the requested
state. A real transition increments the generation, an idempotent no-op keeps
it stable, and a stale writer receives an explicit conflict instead of a
silent overwrite.

## Approach

Migrate the canonical Store schema without changing existing enabled values.
Project the generation through CLI, dashboard, MCP, and host-native status
surfaces. Require an expected generation at authenticated remote mutation
boundaries, map stale dashboard requests to HTTP 409, and keep multi-host CLI
results truthful when only some hosts succeed. Bound the counter and reject
exhaustion rather than wrapping it.

## Dependencies

ADR-0034 established the SQLite-backed host soft-control boundary. ADR-0057
adds its atomic compare-and-swap semantics. The separate Agency-wide master
generation remains governed by ADR-0053.

## Acceptance

- [x] Schema migration adds a bounded non-negative generation without changing legacy host state.
- [x] Every host status projection exposes the committed generation.
- [x] Public mutations require or derive one observed expected generation.
- [x] Comparison and publication occur in one immediate SQLite transaction.
- [x] A real transition increments once and an idempotent no-op preserves the generation.
- [x] Stale, malformed, and exhausted generations fail closed with actionable errors.
- [x] Dashboard conflicts return HTTP 409 and MCP/CLI surfaces preserve truthful failure results.
- [x] Concurrent-writer, full-suite, exact-coverage, installed-smoke, and tracker gates pass.
