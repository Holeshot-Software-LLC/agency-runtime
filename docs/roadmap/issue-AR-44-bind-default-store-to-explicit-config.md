---
title: "AR-44: Bind default Store storage to its explicit configuration"
status: done
category: roadmap
created: 2026-07-15
updated: 2026-07-15
tags: [sqlite, configuration, embedding, correctness]
related:
  - docs/decisions/0006-config-first-redacted-configuration.md
  - docs/decisions/0012-canonical-sqlite-audit-store.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: operations
issue_id: AR-44
priority: p0
tracker_url: "https://github.com/Holeshot-Software-LLC/agency-runtime/issues/45"
depends_on:
  - AR-39
  - AR-40
blocks:
  - AR-45
  - AR-46
  - AR-47
---

# AR-44: Bind default Store storage to its explicit configuration

## Problem

`Store(config_path=custom, db_path=None)` applies roster policy from the custom
configuration but derives its database from the process-default configuration.
One Store can therefore split its policy and evidence across two identities.

## Current state

CLI and dashboard constructors normally pass both the resolved database and
config path. The public Store constructor nevertheless advertises explicit
config binding and is used by embedders, so relying on every caller to duplicate
database resolution is an unsafe hidden precondition.

## Approach

When an explicit config path is supplied and the database is omitted, load the
database path from that exact validated config identity. Preserve explicit
database precedence and fail closed if the bound config is invalid.

## Dependencies

AR-39 removes fallback on invalid configuration, while AR-40 establishes
single-identity dashboard ownership. This closes the equivalent public Store
constructor seam under ADR-0006 and ADR-0012.

## Acceptance

- [x] An explicit Store config determines the default database path.
- [x] A poisoned process-default config cannot reroute an explicitly bound Store.
- [x] An explicit `db_path` still takes precedence without changing config policy binding.
- [x] Invalid bound configuration fails closed without creating fallback storage.
- [x] Full exact-coverage, Windows/Linux, package, and tracker gates pass.
