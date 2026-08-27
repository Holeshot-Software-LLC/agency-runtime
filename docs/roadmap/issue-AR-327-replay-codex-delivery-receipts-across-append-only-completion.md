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
- The regression-first repair selects only the receipt digest's unique
  newline-terminated prefix from one owner-trusted bounded read, reparses only
  those bytes, and keeps public diagnostics, fresh Store consumption, and
  Claude whole-window replay unchanged.
- The affected suite passes 211 tests with the three known AR-323 schema-46
  literals explicitly deselected. Seventeen conformance tests pass and both new
  curated mutations are killed with source unchanged. Focused Ruff and format
  checks pass.
- Committed source `636ce34b` replays the exact retained Qwen2 Store and child
  rollout without a model call or write. Both read-only receipt verification
  and the complete restricted verifier return staffed
  `verified_existing_receipt`; receipt `91bd1c0d...21ac` remains immutable.
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

- [x] Regression proves an existing Codex receipt replays after only complete
      records are appended to its exact verified prefix.
- [x] Mutation, truncation, non-record-boundary, wrong-digest, and identity
      mismatch cases fail closed; Claude's exact-artifact behavior is unchanged.
- [x] The affected warning-strict suite and focused conformance mutations pass.
- [x] Rebuilt exact artifacts/images pass independent verification.
- [ ] One new clean no-bypass Codex install persists current-profile
      attestation and exits 0.
- [ ] A same-repository tracker issue is created and linked after explicit
      authorization.

## Verification

Owner-private evidence is retained under
`~/.agency-runtime/evidence/ar327-append-replay-precheckpoint`. The affected
suite passes 211 tests with 3 AR-323 deselections at stdout
`1b0fd16d...9ab3`; 17 decision tests pass at `f54f2441...aab`; two focused
mutations are killed with zero survived/invalid and source unchanged at
`527ff7d8...a78`; and focused Ruff/format passes at `82b3e6a6...4f18`.
Every command exits 0 with empty stderr.

Exact committed-source Qwen2 replay exits 0 at `f98bb268...7cb3`. It proves
terminal parent/route resolution, trusted canonical artifact, exact Store
decision/receipt, and both verification layers staffed without updating the
failed installed candidate's Store or attestation.

Clean ledger `7dbd0cbc5cbc77e46fc795568bb63ddcf5e3ee6f` produces exact
wheel `e117b362...fc03d` and sdist `ac30feb0...9fb6c`. Canonical build,
strict Twine, independent verification, manifest, all six image builds, and
image verification exit 0; manifest and image receipts are
`780512b2...b7876` and `00fcf8e6...5f76`. The new exact Codex image is
`206e94c4...a5b2e`; its clean one-install proof remains pending.

The retained unfiltered suite exits 1 after 211 passes only because
`test_native_child_delivery_verification_ledger.py` still expects schema 46 in
the three cases already owned by AR-323; stdout hashes to `48dc8017...3b5`.
The first mutation attempt likewise retains an exit-1 private-namespace refusal
at `ce640b84...e538` before its baseline; the owner-private umask-077 rerun is
the authoritative passing mutation receipt.
