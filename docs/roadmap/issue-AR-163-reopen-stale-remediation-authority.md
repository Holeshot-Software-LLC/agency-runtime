---
title: "AR-163: Reopen stale remediation resolution authority"
status: in_progress
category: roadmap
created: 2026-07-27
updated: 2026-07-27
tags: [security, roster, remediation, hmac, observability]
related:
  - docs/roadmap/issue-AR-95-bind-remediation-resolution-authority-to-complete-durable-evidence.md
  - docs/decisions/0066-package-audited-roster-and-sync-quarantined-deltas.md
  - agency_runtime/core/roster/sync.py
  - agency_runtime/core/roster/review.py
  - agency_runtime/core/dashboard_operational.py
  - agency_runtime/dashboard/dashboard-live.js
  - agency_runtime/dashboard/dashboard-render.js
  - tests/dashboard_ui.test.mjs
  - tests/test_roster_remediation.py
supersedes: []
superseded_by: null
type: issue
epic: security
issue_id: AR-163
priority: p1
tracker_url: null
depends_on: []
blocks: []
---

# AR-163: Reopen stale remediation resolution authority

## Problem

A correctly signed remediation-resolution marker continued to suppress its
quarantine queue entry after the bound candidate was rejected or its conflict
audit became stale against the active roster. Approval and activation still
failed closed, so this was not prompt-execution authority, but the operational
queue could incorrectly present a repair as resolved and report no anomaly.
An already paged dashboard could also retain that stale history row after a
refresh if the shortened first page remained a prefix of the loaded rows.

## Current state

The durable HMAC still proves immutable historical evidence. Queue suppression
now additionally requires current candidate eligibility: a pending or approved
candidate must retain its quarantined download and latest passing audit under
the current policy and active-roster basis. An activated candidate remains a
valid terminal resolution only while the exact candidate version and hash are
active, preventing normal activation from creating duplicate review churn.

Cryptographically invalid, cryptographically valid but stale, and currently
resolved records are counted as disjoint categories. Stale signed authority
reopens the original queue event rather than inserting a duplicate.

## Approach

Keep AR-95's HMAC receipt, dependency closure, and immutable resolution history
unchanged. Add a read-time current-eligibility predicate alongside signature
integrity for pending suppression, history pagination, and counts. Surface the
stale count through the read-only dashboard and add adversarial tests for
rejection, active-basis drift, exact replay, HMAC tamper, approval/activation
failure, count arithmetic, and event idempotency. Bind dashboard pagination to
an exact remediation projection revision and suppress any defensive pending /
history overlap rather than presenting contradictory authority.

## Dependencies

AR-95 owns the durable evidence and signature boundary. ADR-0066 requires every
upstream repair to remain quarantined and non-executable until governed review,
approval, and activation complete.

Tracker creation remains pending owner authorization; no outward tracker write
was performed in this local implementation session.

## Acceptance

- Rejected candidates and stale latest audit bases cannot suppress a remediation
  queue entry or appear in current resolution history.
- An exact replay of a previously valid signed marker cannot restore current
  authority after its candidate becomes ineligible.
- A modified HMAC remains rejected by the existing insertion boundary.
- Approval and activation continue to fail closed for rejected or audit-stale
  candidates.
- Reopening projects the original queue event and creates no duplicate queue or
  resolution event.
- Current, stale, and unvalidated resolution counts are disjoint and sum to the
  raw resolution count.
- Expanded remediation pages survive a refresh only when the server proves the
  same current projection revision and the returned first page remains an exact
  prefix; reopening cannot leave one queue event visible as both pending and
  resolved history.
- The dashboard labels stale signed authority separately from unvalidated raw
  records without exposing prompt content or signing material.

## Implementation evidence

The current affected suites pass 134 remediation tests and 32 dashboard
projection tests, including rejection/replay, active-basis drift, revision
invalidation, and bounded disclosure regressions. The complete dashboard UI
suite passes 102 tests. Focused Ruff lint and format checks and scoped
`git diff --check` pass. Full repository integration, the final release gate,
and tracker creation remain pending outside this bounded local slice.
