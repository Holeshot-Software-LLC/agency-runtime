---
title: "AR-40: Bind dashboard reads and writes to one config identity"
status: done
category: roadmap
created: 2026-07-15
updated: 2026-07-15
tags: [dashboard, configuration, concurrency, embedding, correctness]
related:
  - docs/decisions/0006-config-first-redacted-configuration.md
  - docs/decisions/0029-secure-local-dashboard-and-bounded-observability.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: operations
issue_id: AR-40
priority: p0
tracker_url: "https://github.com/Holeshot-Software-LLC/agency-runtime/issues/41"
depends_on:
  - AR-36
blocks:
  - AR-44
  - AR-46
---

# AR-40: Bind dashboard reads and writes to one config identity

## Problem

Dashboard handlers use process-default config reads and writes while roster
policy can come from a Store bound to a custom config. The launcher mutates
process-global `AGENCY_CONFIG_PATH`, so embedded servers can write a different
file or reroute unrelated threads.

## Current state

The service worker carries an explicit config path and the Store can bind that
identity, but `DashboardHTTPServer` does not own it. Configuration handlers and
server limits call default resolvers independently.

## Approach

Bind one canonical config path to each dashboard server, pass it explicitly to
every typed load/read/write, and remove launcher environment mutation. Derive
the identity from explicit launch input or the Store binding, and reject a
mismatch before listening. Prove two embedded servers cannot cross-write.

## Dependencies

AR-36 defines canonical path resolution. This completes ADR-0006 and ADR-0029
for embedded and service dashboard processes.

## Acceptance

- [x] Programmatic and CLI dashboard servers read and mutate exactly one config file.
- [x] Dashboard startup does not mutate process-global configuration environment.
- [x] Store/config identity mismatches fail before serving.
- [x] Concurrent custom-config server regressions pass.
- [x] Full exact-coverage, Windows/Linux, package, and tracker gates pass.
