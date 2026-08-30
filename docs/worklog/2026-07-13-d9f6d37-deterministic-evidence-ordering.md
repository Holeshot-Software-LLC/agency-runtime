---
title: "Worklog: Deterministic evidence event ordering"
status: active
category: worklog
created: 2026-07-13
updated: 2026-07-13
tags: [evidence, sqlite, determinism, windows]
related:
  - docs/decisions/0027-authoritative-runtime-evidence-traces.md
  - docs/roadmap/issue-AR-17-production-hardening-portability.md
  - docs/roadmap/issue-AR-24-deterministic-evidence-ordering.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: worklog
commit: d9f6d37b20136dd3ab8f0411e6199a99892a3718
short: d9f6d37
date: 2026-07-13
pr: "https://github.com/Holeshot-Software-LLC/agency-runtime/pull/18"
related_issues:
  - docs/roadmap/issue-AR-17-production-hardening-portability.md
  - docs/roadmap/issue-AR-24-deterministic-evidence-ordering.md
---

# Worklog: Deterministic evidence event ordering

## Purpose

Make authoritative delegation evidence chronological and deterministic when a
platform clock assigns the same timestamp to consecutive events.

## Approach

Reproduced the hosted Windows result with the production delegation table and
session index: timestamp-only ordering returned equal-key rows newest-first.
Added SQLite row ID as the insertion-order tie-breaker for trace, filtered
session, unfiltered session, and direct header evidence queries. Split the
regressions so ambiguous correlation asserts identities and statuses without
assuming position, while a frozen-clock test owns the ordering contract.

## Challenges encountered

The original failure looked like an arbitrary suggestion had been promoted, but
the adapter had correctly written a separate explicit delegation. Only the
readback order was wrong. Repository-local full-suite roots also approached the
Windows path-length boundary during atomic installer staging; the supported
short elevated temp root produced the valid exact-coverage result.

## Decisions and alternatives

Rejected weakening the ambiguity test or sorting by random UUID text. An
explicit persistent integer sequence would require a schema migration and is
not needed for the current runtime ordering contract; row ID is already the
repository's insertion-order convention for same-timestamp migrations. The
behavioral and ordering regressions remain separate so neither can mask the
other.

## Verification

- Same-index SQLite reproducer: timestamp-only order failed; row-ID tie order passed.
- Evidence-integrity suite: 10 passed.
- Full warning-strict suite: exit 0 with exact 100.00% line and branch coverage.
- Ruff check and format: 259 files passed.
- Documentation metadata, graph, worklog, and tracker parity checks passed.
- Independent final review findings were incorporated before commit.

## Follow-ups

Require the complete hosted matrix to pass, then merge PR 18 and reconcile
AR-17 and AR-24 with final worklog and tracker state.
