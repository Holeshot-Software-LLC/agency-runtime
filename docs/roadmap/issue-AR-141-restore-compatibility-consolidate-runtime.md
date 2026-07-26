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

## Implementation evidence

Thin route_and_build_context() and header finalize() wrappers are restored with
tested deprecation warnings through 0.2.x. Agent identity precedence, bounded
values, filesystem trust, and executable namespace projection now have
canonical helpers used by the changed runtime paths. Compatibility tests pass
4, header/selector tests 91, roster/unit-assignment tests 43, and release
verification passes. The item remains open because repository-wide dead-code
removal evidence and the remaining JSON/helper consolidation have not been
completed.

A repository-wide static reachability audit then proved that seven named
private inference helpers and their private-only dependency chain had no
production, export, dynamic-dispatch, or string-entrypoint path. The bounded
removal deletes 590 production lines while adding one replacement line and ports the remaining shortlist fixtures
to canonical public plan documents. Its owning suite passes 52 tests with one
skip and one expected failure; Ruff and diff checks pass. This satisfies the
dead-code-removal acceptance slice. The issue remains open for the separately
reviewed JSON/helper consolidation and large-function decomposition work.
