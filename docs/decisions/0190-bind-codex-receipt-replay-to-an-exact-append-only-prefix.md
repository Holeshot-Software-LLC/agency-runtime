---
title: "Bind Codex receipt replay to an exact append-only prefix"
status: accepted
category: decisions
created: 2026-08-27
updated: 2026-08-27
tags: [codex, host-artifact, receipt, append-only, security]
related:
  - docs/decisions/0156-host-artifacts-prove-native-child-delivery.md
  - docs/decisions/0179-admit-exact-codex-canary-delivery-at-subagent-start.md
  - docs/decisions/0189-admit-only-accepted-terminal-codex-parents-for-post-return-collection.md
  - docs/roadmap/issue-AR-297-complete-unattended-container-bootstrap.md
  - docs/roadmap/issue-AR-326-admit-terminal-codex-host-artifact-collection.md
  - docs/roadmap/issue-AR-327-replay-codex-delivery-receipts-across-append-only-completion.md
  - docs/roadmap/handoffs/issue-AR-297.md
  - agency_runtime/core/child_delivery_evidence.py
  - tests/test_child_delivery_evidence.py
  - docs/worklog/README.md
supersedes: []
superseded_by: null
id: ADR-0190
type: decision
deciders: [maintainers]
---

# ADR-0190: Bind Codex receipt replay to an exact append-only prefix

## Context

Codex writes a child rollout incrementally. The restricted hook verifier read
and atomically consumed an owner-trusted 84,598-byte window through the child's
terminal token-count record. After that verification, Codex appended its normal
`task_complete` record. The post-return AR-326 collector correctly found the
same accepted parent, route, receipt, child, and rollout, but computed the
SHA-256 of the now-longer file. Every receipt identity still matched except the
artifact digest, so replay failed despite the originally verified bytes being
unchanged.

The receipt is immutable and already binds the exact prior bytes. Treating the
later whole-file digest as the same evidence window is inaccurate; ignoring
digest drift entirely would let mutations inherit authority.

## Decision

Fresh native-child delivery verification continues to hash the exact bounded,
trusted artifact window that it consumes atomically. Read-only replay of an
existing Codex receipt may select an earlier window only when the receipt's
SHA-256 matches exactly one newline-terminated prefix of the current bounded
owner-trusted rollout read.

The verifier reparses only that exact prefix and repeats every structural and
semantic check against the immutable Store decision and receipt. Bytes after
the selected prefix receive no evidentiary authority. No match, more than one
match, a partial-record boundary, invalid decoding or JSONL, changed prefix,
truncation, wrong identity, or untrusted storage fails closed. This exception
is internal to persisted Codex receipt replay; public diagnostics, fresh Store
consumption, and Claude's exact whole-window behavior remain unchanged.

## Consequences

Ordinary Codex completion records can be appended after delivery verification
without invalidating the immutable receipt. A mutation anywhere inside the
receipt-bound prefix changes its digest and remains rejected. An attacker
cannot make later text alter the earlier parsed delivery because the parser is
bounded to the cryptographically selected prefix.

The replay path now depends on newline-delimited Codex JSONL records. A future
Codex format that appends partial records or changes the artifact framing will
fail until its boundary receives separate review.

## Alternatives

Requiring the completed whole-file digest was rejected by the exact live
failure. Updating the immutable receipt after process return was rejected
because it would turn replay into a second authority-bearing write. Ignoring
the digest or trusting any earlier parseable prefix was rejected because
mutated artifacts could inherit proof. Defining a semantic endpoint by record
type was rejected because it would couple authority to mutable host event
ordering instead of the Store's already-consumed exact bytes.
