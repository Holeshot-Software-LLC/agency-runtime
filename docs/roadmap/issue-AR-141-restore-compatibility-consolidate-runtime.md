---
title: "AR-141: Restore compatibility and consolidate runtime duplication"
status: done
category: roadmap
created: 2026-07-26
updated: 2026-08-12
tags: [maintenance, compatibility, refactoring, dead-code, duplication]
related:
  - CHANGELOG.md
  - agency_runtime/core/selector
  - agency_runtime/core/header
  - agency_runtime/core/store
  - agency_runtime/core/bounded_json.py
  - agency_runtime/core/filesystem_trust.py
  - agency_runtime/adapters/hooks.py
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

Restore thin deprecated compatibility wrappers for one declared cycle, then
centralize identity and security-sensitive primitives with contract tests.
Remove only independently proven dead private code. Extract pure projection,
identity, parsing, and lifecycle helpers where ownership was duplicated; retain
cohesive transaction and authority functions when splitting them would add
handoff state without reducing production risk.

## Dependencies

Complete P0 behavioral fixes before mechanical consolidation.

## Acceptance

- [x] Public compatibility policy and deprecation window are documented and tested.
- [x] One canonical agent identity precedence is used everywhere.
- [x] Filesystem trust and lexical path primitives have one owner; domain wrappers
  retain only their additional validation and error contracts.
- [x] Persisted and externally supplied JSON uses one bounded parser owner, with an
  exact test-enforced allowlist for dependency-isolated generated shims.
- [x] Routing/roster digest, workforce snapshot, and hook child-identity protocols
  have one canonical owner without changing serialized bytes or host scheduling.
- [x] Dead-code removals have repository-wide call-graph and behavior evidence.
- [x] Refactors preserve coverage, routing outcomes, and release artifacts.

## Implementation evidence

Thin route_and_build_context() and header finalize() wrappers are restored with
tested deprecation warnings through 0.2.x. Agent identity precedence, bounded
values, filesystem trust, and executable namespace projection now have
canonical helpers used by the changed runtime paths. Compatibility tests pass
4, header/selector tests 91, roster/unit-assignment tests 43, and release
verification passes.

A repository-wide static reachability audit then proved that seven named
private inference helpers and their private-only dependency chain had no
production, export, dynamic-dispatch, or string-entrypoint path. The bounded
removal deletes 590 production lines while adding one replacement line and
ports the remaining shortlist fixtures to canonical public plan documents. Its
owning suite passes 52 tests with one skip and one expected failure; Ruff and
diff checks pass.

The final consolidation gives lexical path/link/same-object trust, persisted
bounded JSON, routing and roster projection digests, workforce-generation
binding, and native-child lifecycle identity one protocol owner. Child-routing
writers now prove the exact reader byte/depth/node contract before persistence;
over-wide JSON is rejected before parser materialization; duplicate and
non-finite errors are typed; generated-parser exceptions are AST-inventoried;
and native hook output is sized before a one-use grant is minted. The host still
owns delegation topology and execution.

Three independent post-diff reviews found zero Critical, High, or Medium issues
after remediation. Focused authority/path/JSON suites pass, the named Python
production spine passes 522 tests with five platform skips, all 106 dashboard
tests pass, and the routing evaluation passes every correctness, delegation,
scale, startup, and performance gate. Large route/schema transaction bodies
were reviewed but deliberately not split solely for line count; no duplicate
production-sensitive helper identified by the AR-141 audit remains unowned.
