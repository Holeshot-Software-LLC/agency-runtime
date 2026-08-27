---
title: "Replay immutable Codex delivery prefixes"
status: active
category: worklog
created: 2026-08-27
updated: 2026-08-27
tags: [ar-297, ar-327, codex, host-artifact, receipt, security]
related:
  - docs/roadmap/issue-AR-297-complete-unattended-container-bootstrap.md
  - docs/roadmap/issue-AR-327-replay-codex-delivery-receipts-across-append-only-completion.md
  - docs/roadmap/handoffs/issue-AR-297.md
  - docs/decisions/0156-host-artifacts-prove-native-child-delivery.md
  - docs/decisions/0190-bind-codex-receipt-replay-to-an-exact-append-only-prefix.md
supersedes: []
superseded_by: null
type: worklog
commit: 636ce34b9dbfba2a834ab8b2a2559a9f73febce4
short: 636ce34b
date: 2026-08-27
pr: null
related_issues:
  - docs/roadmap/issue-AR-297-complete-unattended-container-bootstrap.md
  - docs/roadmap/issue-AR-327-replay-codex-delivery-receipts-across-append-only-completion.md
---

# Worklog detail: Replay immutable Codex delivery prefixes

## Purpose

Allow the exact post-return Codex collector to re-project an already-consumed
native-child delivery receipt after Codex appends ordinary completion records,
without treating the later suffix as delivery evidence or weakening mutation
detection inside the verified bytes.

## Approach

Fresh verification still hashes and atomically consumes its entire trusted
bounded read. Existing Codex receipt replay validates the immutable receipt
digest, locates its unique newline-terminated prefix inside one later trusted
read, and reparses only that exact prefix. The expected decision and sealed
read-only consumer then repeat every existing identity, nonce, card, timing,
binding, and structural-origin check against the receipt-bound digest.

Public Codex diagnostics, fresh Store consumption, and Claude replay retain
their existing whole-window behavior. Two curated mutations pin both the use of
the immutable digest and the complete-JSONL boundary. ADR-0190 owns the durable
append-only evidence rule.

## Challenges encountered

The exact Qwen2 rollout revealed that the live receipt covered 16 complete
records through token count, while Codex appended a seventeenth
`task_complete` record before post-return collection. An initial focused
mutation evaluation inherited umask 022, so its copied checkout failed the
private-path fixture before baseline execution. That refusal remains retained;
the authoritative umask-077 rerun passed without a source change.

The unfiltered affected suite also retained the three known AR-323 failures
whose tests hard-code schema 46 while the Store is schema 48. The same suite
passes with only those unrelated literal assertions deselected.

## Decisions and alternatives

ADR-0190 rejects updating the immutable receipt, ignoring digest drift, or
selecting a semantic host event as a new authority boundary. Cryptographic
selection of the already-consumed complete-record prefix preserves both exact
prior bytes and append tolerance.

## Verification

- The affected warning-strict suite passes 211 tests with 3 known AR-323
  deselections at stdout SHA-256 `1b0fd16d...9ab3`; stderr is empty.
- Seventeen decision-conformance tests pass at `f54f2441...aab`.
- Both focused mutations are killed with zero survived/invalid and source
  unchanged at `527ff7d8...a78`.
- Focused Ruff and format checks pass at `82b3e6a6...4f18`.
- The unfiltered 211-pass/3-failure AR-323 receipt and the first private-path
  refusal remain retained at `48dc8017...3b5` and `ce640b84...e538`.

## Follow-ups

- Replay the exact retained Qwen2 Store and rollout through this committed
  source without invoking a model or relabelling the failed install.
- Rebuild and independently verify exact artifacts and images, then use one new
  clean no-bypass Codex container for current-profile attestation.
- Continue the remaining AR-297 harness, ordinary-process, host/dashboard,
  repository-gate, and teardown packages.
- Tracker creation remains prohibited and was not attempted.
