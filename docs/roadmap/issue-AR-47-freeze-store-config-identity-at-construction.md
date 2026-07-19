---
title: "AR-47: Freeze Store configuration identity at construction"
status: done
category: roadmap
created: 2026-07-15
updated: 2026-07-15
tags: [sqlite, configuration, environment, concurrency, embedding]
related:
  - docs/decisions/0006-config-first-redacted-configuration.md
  - docs/decisions/0012-canonical-sqlite-audit-store.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: operations
issue_id: AR-47
priority: p0
tracker_url: "https://github.com/Holeshot-Software-LLC/agency-runtime/issues/48"
depends_on:
  - AR-44
  - AR-45
  - AR-46
blocks:
  - AR-53
---

# AR-47: Freeze Store configuration identity at construction

## Problem

A default `Store()` chooses its database from the current process configuration
but retains no config path. Later roster and privacy reads resolve process state
again, so an environment/config-identity change can split one live Store across
different storage and policy identities.

## Current state

Explicit config paths are bound by AR-44/AR-45. The `None` constructor path was
retained as a compatibility mode even though a long-lived Store needs a stable
identity for correct concurrency and embedding behavior.

## Approach

Resolve and bind the effective config path for every real Store at construction,
including the conventional default. Continue reloading values from that file so
atomic dashboard edits take effect, but never follow a later path-selection
environment change. Validate the bound document before creating or migrating
any database file, and use that validated snapshot for constructor-time privacy
decisions. Require server constructors to pass the intended identity instead of
rebinding an already initialized Store.

## Dependencies

AR-44 through AR-46 bind default storage, privacy, and routing. This item makes
that identity immutable for the Store lifetime under ADR-0006 and ADR-0012.

## Acceptance

- [x] Every Store has one canonical configuration path for its full lifetime.
- [x] Later `AGENCY_CONFIG_PATH` changes cannot reroute DB, roster, privacy, or routing reads.
- [x] Invalid bound configuration fails before any database creation or migration.
- [x] Atomic edits to the bound file remain visible without reconstructing the Store.
- [x] Unchanged bound reads reuse a file-aware cache without crossing config identities.
- [x] Dashboard/HTTP/MCP constructors reject mismatches before serving.
- [x] Full exact-coverage, Windows/Linux, package, and tracker gates pass.
