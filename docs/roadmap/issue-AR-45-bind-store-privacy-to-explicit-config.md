---
title: "AR-45: Bind Store privacy projection to its explicit configuration"
status: done
category: roadmap
created: 2026-07-15
updated: 2026-07-15
tags: [privacy, sqlite, configuration, embedding, security]
related:
  - docs/decisions/0006-config-first-redacted-configuration.md
  - docs/decisions/0012-canonical-sqlite-audit-store.md
  - docs/decisions/0027-authoritative-runtime-evidence-traces.md
  - docs/THREAT_MODEL.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: operations
issue_id: AR-45
priority: p0
tracker_url: "https://github.com/Holeshot-Software-LLC/agency-runtime/issues/46"
depends_on:
  - AR-44
blocks:
  - AR-47
---

# AR-45: Bind Store privacy projection to its explicit configuration

## Problem

An explicitly configured Store still consults the process-default config when
deciding whether runtime content may be persisted. A permissive default can
therefore override a custom config whose `capture_content` policy is false.

## Current state

The Store binds roster policy and, after AR-44, its default database to one
config identity. Privacy projection retains a compatibility wrapper that loads
global configuration independently.

## Approach

Resolve content-capture policy from the Store-bound config for every write and
migration. Preserve the legacy process-default behavior only for Stores created
without an explicit config identity. Prove the restrictive bound policy wins
even when the process default is deliberately permissive.

## Dependencies

AR-44 establishes complete default storage identity. This item completes the
privacy half of the same Store boundary under ADR-0006, ADR-0012, and ADR-0027.

## Acceptance

- [x] Explicit Store config controls content capture for all runtime projections.
- [x] A permissive process default cannot override a restrictive bound Store.
- [x] Unbound legacy Store behavior remains compatible.
- [x] Schema migration applies the same bound privacy policy.
- [x] Full exact-coverage, Windows/Linux, package, security, and tracker gates pass.
