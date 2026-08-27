---
title: "AR-327: Replay Codex delivery receipts across append-only completion"
status: in_progress
category: roadmap
created: 2026-08-27
updated: 2026-08-27
tags: [bug, codex, canary, host-artifact, receipt, security]
related:
  - docs/roadmap/issue-AR-297-complete-unattended-container-bootstrap.md
  - docs/roadmap/issue-AR-326-admit-terminal-codex-host-artifact-collection.md
  - docs/roadmap/handoffs/issue-AR-297.md
  - docs/decisions/0156-host-artifacts-prove-native-child-delivery.md
  - docs/decisions/0189-admit-only-accepted-terminal-codex-parents-for-post-return-collection.md
  - docs/decisions/0190-bind-codex-receipt-replay-to-an-exact-append-only-prefix.md
  - agency_runtime/core/child_delivery_evidence.py
  - tests/test_child_delivery_evidence.py
  - tests/test_canary_activation_snapshot.py
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: host-integrations
issue_id: AR-327
priority: p0
tracker_url: null
depends_on: [AR-326]
blocks: [AR-297]
---

# AR-327: Replay Codex delivery receipts across append-only completion

## Problem

The exact AR-326 post-return collector now locates the accepted terminal Codex
parent and its canonical child rollout, but it re-hashes the rollout after the
host appends its ordinary terminal record. The immutable delivery receipt binds
the exact trusted file window observed at `SubagentStop`; requiring that digest
to equal the later completed file rejects an unchanged verified prefix.

## Current state

- Clean Qwen2 container `9806a82a...2a2b` ran exactly one no-bypass install
  with `--activation-timeout 300`. Codex exits 0 without timeout; one native
  route, one verified delivery, full prompt hash `e409b2c8...20bd`, exit-0
  child, accepted finalization `38c5914f...465c` with `missing=[]`, and one
  completed Store run agree. Installation exits 1 only because current-profile
  attestation is not persisted.
- Content-free diagnostic `dcc4d23a...23b6` proves all nine durable identity
  fields plus the nonce agree between the receipt and the replay request.
  Only `artifact_digest` differs: the receipt retains `91bd1c0d...21ac` while
  the later completed rollout yields `ee5d577e...005d`.
- The receipt digest equals the completed rollout's exact 84,598-byte,
  16-record JSONL prefix. Codex appended only its seventeenth
  `event_msg/task_complete` record after the verified window.
- Store `6730ee75...3195` and parent/child rollouts `aeda3b86...fa59` and
  `ee5d577e...005d` are retained. The Store copy passes quick-check.
- Tracker creation is prohibited by the active AR-297 task.

## Approach

Keep fresh verification bound to the exact trusted window observed and
atomically consumed by the Store. For read-only replay of an existing Codex
receipt, require its immutable SHA-256 to identify exactly one complete JSONL
prefix inside the current owner-trusted bounded read. Reparse and verify only
those exact bytes, then require every existing decision, nonce, host, parent,
trace, launch, binding, child, card, timing, and structural-origin check.

Reject a missing or ambiguous prefix, a digest at a partial-record boundary,
mutation within the receipt-bound bytes, truncation, malformed UTF-8 or JSONL,
identity drift, and an untrusted path. Do not grant suffix bytes any evidence
authority. Keep Claude and fresh Store consumption on their existing exact
whole-window semantics.

## Dependencies

- AR-326 supplies the accepted-terminal lookup and exact post-return collector
  that exposes this later immutable-receipt replay mismatch.
- ADR-0156 continues to require independently read host-authored bytes; a Store
  receipt can select its prior byte window but cannot replace or invent it.

## Acceptance

- [ ] Regression proves an existing Codex receipt replays after only complete
      records are appended to its exact verified prefix.
- [ ] Mutation, truncation, non-record-boundary, wrong-digest, and identity
      mismatch cases fail closed; Claude's exact-artifact behavior is unchanged.
- [ ] The affected warning-strict suite and focused conformance mutations pass.
- [ ] Rebuilt exact artifacts/images pass independent verification.
- [ ] One new clean no-bypass Codex install persists current-profile
      attestation and exits 0.
- [ ] A same-repository tracker issue is created and linked after explicit
      authorization.
