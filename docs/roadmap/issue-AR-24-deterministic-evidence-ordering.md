---
title: "AR-24: Make evidence event ordering deterministic"
status: done
category: roadmap
created: 2026-07-13
updated: 2026-07-14
tags: [evidence, sqlite, windows, determinism, reliability]
related:
  - docs/decisions/0027-authoritative-runtime-evidence-traces.md
  - docs/roadmap/issue-AR-17-production-hardening-portability.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: observability
issue_id: AR-24
priority: p0
tracker_url: "https://github.com/Holeshot-Software-LLC/agency-runtime/issues/25"
depends_on: []
blocks: [AR-17]
---

# AR-24: Make evidence event ordering deterministic

## Problem

Delegation evidence queries order only by their timestamp. Windows clocks can
assign the same timestamp to back-to-back events, allowing SQLite's descending
session index to surface equal-key rows in reverse insertion order. Consumers
can then observe a later explicit delegation between earlier suggestions even
though correlation safely left both suggestions untouched.

## Current state

Hosted Windows Python 3.10 exposed the tie after all Windows Python 3.14 tests
passed. The ambiguous-delegation regression received two same-session
suggestions, correctly recorded a separate delegated fallback event, and then
observed the three rows in nondeterministic order.
The row-ID tie-breaker and frozen-clock regressions now make every supported
consumer deterministic, and the complete hosted matrix passed.

## Approach

Order trace-scoped and session-scoped delegation evidence by timestamp followed
by SQLite row ID. The timestamp retains chronological meaning and row ID gives
same-timestamp events their insertion order. Freeze the clock in a dedicated
query-order regression so the tie is reproduced on every platform across trace,
filtered-session, unfiltered-session, and header consumers. Keep the separate
ambiguity regression position-independent and assert suggestion identities and
statuses directly.

## Dependencies

This applies ADR-0027's authoritative correlated-evidence contract. The
deterministic ordering regressions and complete hosted matrix passed before
pull request #18 merged.

## Acceptance

- [x] The same-timestamp query-plan behavior is reproduced and diagnosed.
- [x] Trace and session delegation queries use an insertion-order tie-breaker.
- [x] Ambiguous execution leaves both suggestions untouched and records a separate event.
- [x] Focused and warning-strict exact-coverage tests pass.
- [x] Hosted Windows Python 3.10 and the complete PR matrix pass.
- [x] Review, merge, roadmap/worklog reconciliation, and tracker closure pass.
