---
title: "AR-97: Reconcile required-inference remediation in one ingestion"
status: in_progress
category: roadmap
created: 2026-07-18
updated: 2026-07-19
tags: [roster, quarantine, remediation, inference]
related:
  - docs/roadmap/issue-AR-86-govern-complete-upstream-roster-lifecycle.md
  - docs/roadmap/issue-AR-95-bind-remediation-resolution-authority-to-complete-durable-evidence.md
  - docs/decisions/0066-package-audited-roster-and-sync-quarantined-deltas.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: roster-governance
issue_id: AR-97
priority: p1
tracker_url: "https://github.com/Holeshot-Software-LLC/agency-runtime/issues/98"
depends_on: [AR-86, AR-95]
blocks: []
---

# AR-97: Reconcile required-inference remediation in one ingestion

## Problem

A known repaired or superseding candidate can pass its required inference audit
while the earlier quarantine remediation entry remains falsely pending until a
later ingestion. The first reconciliation runs before authoritative inference
evidence exists, but the completed inference audit did not trigger a second
transactional reconciliation.

## Current state

The post-audit reconciliation boundary now rechecks only the persisted scan and
candidate identities from the same import. Focused regressions prove a single
authorized resolution, no stale pending entry, bounded idempotence, and
fail-closed behavior when required inference is unavailable or unsuccessful.
The full repository suite and fresh wheel/source installed-artifact smoke pass;
the hosted cross-platform release matrix remains.

## Approach

After the configured audit batch completes, reconcile only the persisted scan
and candidate identities from that same import. Reuse the existing bounded
queue validation, current-audit checks, append-only resolution event, and
authenticated dependency authority. Keep the operation atomic and idempotent;
failed, unavailable, stale, or ambiguous inference evidence must leave the
entry quarantined and pending.

## Dependencies

AR-86 owns the governed upstream lifecycle. AR-95 and ADR-0066 own the durable,
fail-closed remediation evidence contract.

## Acceptance

- [x] Required-inference ingestion reconciles an eligible repair in the same top-level call.
- [x] Reconciliation is persisted-evidence-bound, atomic, idempotent, and bounded.
- [x] Failed or unavailable required inference leaves quarantine pending.
- [x] The regression proves exactly one authorized resolution and zero pending entries.
- [ ] The complete release matrix and installed-artifact smoke pass.
