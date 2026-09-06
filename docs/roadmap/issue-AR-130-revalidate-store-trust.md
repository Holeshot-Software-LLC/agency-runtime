---
title: "AR-130: Revalidate Store trust at authoritative boundaries"
status: open
category: roadmap
created: 2026-07-26
updated: 2026-09-05
tags: [security, sqlite, filesystem, trust, performance]
related:
  - docs/THREAT_MODEL.md
  - docs/decisions/0092-do-not-cache-positive-filesystem-trust.md
  - docs/roadmap/issue-AR-140-scale-routing-and-retrieval.md
  - docs/roadmap/issue-AR-176-align-full-gate-contract-fixtures.md
  - docs/roadmap/AR-404-oldest-first-reconciliation-20260905.md
  - agency_runtime/core/store/sqlite.py
  - agency_runtime/core/store/security.py
  - agency_runtime/core/filesystem_trust.py
  - tests/test_storage_parent_trust.py
  - tests/test_storage_file_trust.py
supersedes: []
superseded_by: null
type: issue
epic: security
issue_id: AR-130
priority: p0
tracker_url: null
depends_on: []
blocks: []
---

# AR-130: Revalidate Store trust at authoritative boundaries

## Problem

The original defect cached positive SQLite storage trust by a path identity
that did not change when directory permissions or DACL authority changed.
A trusted result could survive a later loss of the property it authorized.

## Current state

September 5 oldest-first review at d38e9d13: the positive-cache repair is
implemented, not new work. `_storage_file_is_trusted` calls the authoritative
platform predicate directly. `_connect` rechecks paths and files before opening
SQLite and compares database identity afterward; stable-identity retries do
not reuse an earlier trust decision. `_current_schema_state` also revalidates.
The journal-ready flag avoids repeated PRAGMA setup, not authorization checks.

Current non-Windows evidence: the stable-identity, real same-inode/same-mtime
mode regression, existing-connection authority regression, and complete
`test_storage_file_trust.py` package pass **19 tests in 0.23s**. The broader
parent/file package passes 40, fails two, and deselects 39 Windows-named cases
in 0.84s. Its two stale fixtures are explicitly owned by AR-176: the directory
test masks `getxattr` on the old module instead of the shared ACL helper, and
the file test still rejects 0644 despite the current owner-only-writable
integrity contract inside a separately private Store namespace. The first
therefore probes a nonexistent synthetic directory and correctly fails closed
on ENOENT. A diagnostic using the intended absent-ACL double at the actual
helper boundary passes that existing permission-chain test; this is not a
passing receipt for the unmodified broader suite. No runtime or test changes.

Retain this record open for owner-held native Windows DACL/authority evidence
and current installed hook-budget evidence, followed by isolated acceptance.
The four original criteria below are unchanged. The AR-140 timings below are
historical measurements, not a September performance or five-host certificate.
The record is pre-tracker legacy data; do not create a duplicate tracker.

Original reproduction: a same-inode/same-mtime permission transition returned
trusted before and after the transition and invoked the authoritative trust
check only once. The then-existing audit draft recommended this cache as a performance
optimization; that recommendation is explicitly rejected by current evidence.

## Approach

The original repair was to remove positive authorization caching or bind it to
a complete authoritative permission fingerprint and revalidation contract. Recover latency through
transaction batching and coherent request scopes, never by reusing stale trust.

Remaining sequence: repair the stale fixtures under AR-176 without weakening
the current boundary; let the owner obtain native Windows evidence; obtain a
bounded current-artifact hook measurement through AR-140/AR-253; then run the
isolated criteria before any done flip. Do not restore trust caching to meet
a timing target or run an exhaustive corpus as a routine handoff requirement.

## Dependencies

ADR-0092 governs filesystem trust caching. AR-133 owns atomic finalization;
AR-140 owns measured connection and startup batching that must preserve this
issue's revalidation boundary.

## Acceptance

- Changing relevant POSIX mode, owner, Windows DACL, parent identity, or link
  state invalidates prior trust without restarting the process.
- Every Store connection fails closed after a trust regression.
- Stable-path regression tests cover same-inode and same-mtime transitions.
- Performance remains within the measured hook budget through safe batching.

## Implementation evidence

Historical implementation evidence: positive trust caching has been removed.
Every Store connection re-runs the authoritative platform check, including same-inode/same-mtime authority
regressions. Focused Store security suites and the combined checkpoint suite
pass. AR-140 later replaced nine separately trusted packaged-contractor reads
with one bounded snapshot: the measured stable operational snapshot fell from
539.410 ms to 408.184 ms while every Store connection retained authoritative
trust validation. Supported-runner and final current-artifact evidence remain;
no positive trust cache was reintroduced.
