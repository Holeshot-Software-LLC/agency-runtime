---
title: "AR-95: Bind remediation resolution authority to complete durable evidence"
status: done
category: roadmap
created: 2026-07-18
updated: 2026-07-20
tags: [roster, remediation, security, sqlite, provenance]
related:
  - docs/roadmap/issue-AR-86-govern-complete-upstream-roster-lifecycle.md
  - docs/roadmap/issue-AR-91-enforce-governed-roster-activation.md
  - docs/roadmap/issue-AR-92-redact-roster-source-credentials.md
  - docs/roadmap/issue-AR-93-reject-invisible-unicode-controls.md
  - docs/roadmap/issue-AR-97-reconcile-required-inference-remediation.md
  - docs/decisions/0012-canonical-sqlite-audit-store.md
  - docs/decisions/0066-package-audited-roster-and-sync-quarantined-deltas.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: security
issue_id: AR-95
priority: p0
tracker_url: "https://github.com/Holeshot-Software-LLC/agency-runtime/issues/96"
depends_on: [AR-86, AR-91, AR-92, AR-93]
blocks: [AR-97]
---

# AR-95: Bind remediation resolution authority to complete durable evidence

## Problem

A raw `manifest_entry_remediation_resolved` event is an audit claim, not proof
that the queue item, candidate, scan, audit, transformation, and source evidence
were validated together. Treating the event's mere existence as resolution
authority lets malformed or duplicated rows suppress a pending repair, and
row-order or partial-evidence checks can change after database maintenance.

## Current state

Resolution authority is now a separate HMAC-authenticated projection with one
exclusive queue binding and an exact child dependency closure. Pending and
history queries trust only a valid marker whose receipt, dependency count, child
edges, causal timestamps, agent identity, and durable event sequence all verify.
Raw or ambiguous resolution events remain visible as quarantined anomalies and
never suppress the queue. Focused remediation, forged-provenance, duplicate,
rollback, dependency-loss, and `VACUUM` regressions pass. The repository-wide
suite, built artifacts, and installed Windows smoke also pass; hosted Linux
evidence remains. Bundled-loader and dashboard checks include re-signed
Unicode-control tampering and visible unvalidated-resolution anomaly counts.

## Approach

Validate the complete semantic resolution once, fully validate each distinct
source scan, and bind the normalized scan header and every entry row into a
durable scan seal while keeping selected provenance as explicit dependencies.
Mint authority only through the verifier-held HMAC key. Store every dependency
as a child edge, invalidate the marker when any governed input changes, and use
a monotonic immutable event sequence instead of SQLite row order. Keep raw event
indexes non-unique so forged duplicates cannot reserve a queue identity.

Use bounded, index-compatible JSON predicates before any `json_extract`, cap
resolution work per ingestion transaction, and expose unvalidated resolution
counts through the CLI and dashboard without rendering source prompt content.

## Dependencies

AR-86 owns the remediation lifecycle, AR-91 owns activation fail-closure, AR-92
owns the current durable store migration, and AR-93 owns the source scanner whose
findings and exact bytes enter quarantine evidence.

## Acceptance

- [x] Raw resolution rows never suppress pending work without validated authority.
- [x] Authority is HMAC-bound to one queue, one resolution, and an exact dependency closure.
- [x] Full scan seals exclude unrelated provenance but bind every normalized entry row.
- [x] Every selected provenance event has a positive durable sequence before its scan header.
- [x] Dependency mutation or child-edge loss reopens the queue without trusting stale history.
- [x] Ambiguous exact-detail duplicates cause a fresh canonical resolution rather than order-based reuse.
- [x] Event order survives `VACUUM`, and JSON lookups are bounded and expression-indexed.
- [x] CLI and dashboard projections report unvalidated resolution anomalies without raw prompt content.
- [x] Full coverage, documentation, packaging, Windows, and Linux gates pass.
