---
title: "Worklog detail: Repair integrated production regressions"
status: active
category: worklog
created: 2026-07-26
updated: 2026-07-26
tags: [production-readiness, integration, dashboard, zcode, performance]
related:
  - docs/analysis/2026-07-26-production-readiness-review.md
  - docs/roadmap/handoffs/issue-AR-119.md
  - docs/roadmap/README.md
supersedes: []
superseded_by: null
type: worklog
commit: 0b9849c
short: 0b9849c
date: 2026-07-26
pr: null
related_issues:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-135-complete-zcode-integration.md
  - docs/roadmap/issue-AR-137-complete-dashboard-collections.md
  - docs/roadmap/issue-AR-140-scale-routing-and-retrieval.md
  - docs/roadmap/issue-AR-142-instrument-runtime-boundaries.md
  - docs/roadmap/issue-AR-143-require-operator-presence-for-controls.md
---

# Worklog detail: Repair integrated production regressions

## Purpose

Repair every failure owner exposed by the first complete post-checkpoint
Python run and restore one mixed integration arm before repeating the full
production gate.

## Approach

Stale tests now assert the current fail-closed dashboard, broker, CLI, hook,
schema-37, and atomic-finalization contracts instead of reviving removed
mutation paths. The complete run also found real source omissions: the
interactive wizard now presents ZCode, dashboard request identity tolerates
pre-header disconnects, broker scope is evaluated only after authentication,
and expected client disconnects produce bounded degraded observations.

Large 263- and 1,001-worker paging tests prove exact totals, facets, stable
keyset drains, revision changes, and inter-page insert semantics. Routing
eligibility now issues an internal cache-coherence receipt only after a
detached full-catalog proof; fingerprint reuse consumes that receipt instead
of immediately repeating the same scan. Opaque inputs retain the conservative
snapshot path, catalog mutation issues a new receipt, policy mutation is still
validated, and cached return values remain recursively detached.

## Challenges encountered

The first full run passed 7,486 tests but failed 34 after 43m39s. Most failures
were stale expectations, but treating them as harmless would have hidden the
ZCode wizard and dashboard defects. After those repairs, the mixed arm exposed
a 2.103 ms cache-hit p95 against the unchanged 2.0 ms gate. The threshold was
not relaxed; one redundant validation scan was removed with mutation tests.

## Decisions and alternatives

The eligibility receipt is cache coherence only and is not an authorization
capability. Positive trust caching, weaker mutation checks, performance-limit
changes, and restoring dashboard/broker writes were rejected. AR-143 remains
fail-closed because no genuine production operator-presence backend exists.

## Verification

- Exact 12-module integrated reproducer: 424 passed in 70.71 seconds.
- Focused routing, cache, and dashboard-disconnect package: 79 passed.
- Five unchanged final-source cache-hit p95 controls: 1.345, 1.448, 1.318,
  1.442, and 1.745 ms; every run deterministic.
- Dashboard collection package: 137 passed, 3 skipped.
- Ruff check and format check passed across 558 files.
- Documentation metadata and validation passed for 369 Markdown files.
- Policy availability, worklog, and git diff checks passed.

## Follow-ups

Repeat the complete Python suite and every release/browser/routing gate from
this checkpoint. Current-source reinstall, native canaries, and installed UI
QA remain blocked by AR-143's missing OS-backed operator-presence verifier and
normal-profile Codex's user-owned trust review. AR-119 and AR-125 still need a
benchmark-valid matched corpus. Outward tracker, push, PR, hosted check, tag,
publication, and release actions remain unauthorized.
