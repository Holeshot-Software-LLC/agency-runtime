---
title: "AR-141: Restore compatibility and consolidate runtime duplication"
status: open
category: roadmap
created: 2026-07-26
updated: 2026-07-26
tags: [maintenance, compatibility, refactoring, dead-code, duplication]
related:
  - CHANGELOG.md
  - agency_runtime/core/selector
  - agency_runtime/core/header
  - agency_runtime/core/store
supersedes: []
superseded_by: null
type: issue
epic: maintenance
issue_id: AR-141
priority: p1
tracker_url: null
depends_on: []
blocks: []
---

# AR-141: Restore compatibility and consolidate runtime duplication

## Problem

Recent cleanup removed public `route_and_build_context` and `header.finalize`
surfaces without deprecation or a declared breaking release. Agent identity
precedence differs between `slug` and `agent_slug` call sites, POSIX trust
logic is triplicated, and several private wrappers remain test-only or dead.

## Current state

The internal call graph does not need the removed public helpers, but downstream
callers have no migration window. Duplicated path, identity, bounded-string,
and JSON helpers carry subtly different semantics. Large route/preflight/hook
functions make those differences harder to review.

## Approach

Restore thin deprecated compatibility wrappers for one declared cycle or mark a
major-version break explicitly, then centralize identity and security-sensitive
helpers with contract tests. Remove only independently proven dead private code
and decompose large functions along transaction/authority boundaries.

## Dependencies

Complete P0 behavioral fixes before mechanical consolidation.

## Acceptance

- Public compatibility policy and deprecation window are documented and tested.
- One canonical agent identity precedence is used everywhere.
- POSIX trust, path identity, bounded string, and JSON helpers have one owner.
- Dead-code removals have repository-wide call-graph and behavior evidence.
- Refactors preserve coverage, routing outcomes, and release artifacts.
