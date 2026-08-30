---
title: "AR-145: Restore the Python release coverage gate"
status: open
category: roadmap
created: 2026-07-26
updated: 2026-07-26
tags: [testing, coverage, release, concurrency, observability]
related:
  - tests/test_dashboard.py
  - tests/test_preflight_bounds.py
  - tests/test_selector_coverage_complete_basics.py
  - tests/test_release_coverage_authority_boundaries.py
  - docs/RELEASE_CHECKLIST.md
supersedes: []
superseded_by: null
type: issue
epic: testing
issue_id: AR-145
priority: p0
tracker_url: null
depends_on: []
blocks: []
---

# AR-145: Restore the Python release coverage gate

## Problem

The exact branch-aware Python release command fails despite the non-instrumented
complete suite passing. Its first current-source run reported four failed tests
and 96.66 percent aggregate coverage against the fixed 97 percent floor.

## Current state

The run passed 7,515 tests with 61 skips, 3 intentionally deselected performance
tests, and 1 expected failure. Coverage scheduling exposed an asynchronous
dashboard-observation race and a cold-bootstrap-dependent preflight fixture.
A synthetic routing accuracy test accidentally executed real semantic and CLI
wall-clock gates under instrumentation. Newly added production boundaries also
lack enough behavioral branch coverage for the declared release floor.

## Approach

Synchronize tests on authoritative events instead of arbitrary downstream
timing, isolate wall-clock performance gates from branch instrumentation while
testing their report contracts deterministically, and cover security-relevant
failure branches in finalization, Store maintenance, SQLite observation, MCP,
and dashboard collections. Keep the production coverage threshold, source
selection, and exclusions unchanged.

## Dependencies

The release checklist defines the exact command and fixed 97 percent floor.
AR-144 owns the independent JavaScript release-coverage gate.

## Acceptance

- The exact non-performance Python coverage command exits successfully.
- Aggregate branch-aware coverage is at least 97 percent without exclusions or
  threshold changes.
- Dashboard observations and concurrent preflight ownership tests are
  deterministic under coverage instrumentation.
- Synthetic routing tests do not execute real wall-clock gates.
- The separate uninstrumented performance suite passes its fixed budgets.

## Implementation evidence

Focused repairs pass 33 integrated tests. The dashboard observation now waits
for its matching request boundary, the preflight fixture synchronizes on
persisted ownership after pre-seeding the canonical roster, and the synthetic
routing report uses deterministic shaped retrieval and CLI results. Final
aggregate coverage and performance evidence remain pending.
