---
title: "Admit only accepted terminal Codex parents for post-return collection"
status: accepted
category: decisions
created: 2026-08-27
updated: 2026-08-27
tags: [codex, canary, host-artifact, finalization, lifecycle, security]
related:
  - docs/decisions/0156-host-artifacts-prove-native-child-delivery.md
  - docs/decisions/0179-admit-exact-codex-canary-delivery-at-subagent-start.md
  - docs/decisions/0188-separate-codex-hook-parent-and-child-identities.md
  - docs/roadmap/issue-AR-297-complete-unattended-container-bootstrap.md
  - docs/roadmap/issue-AR-326-admit-terminal-codex-host-artifact-collection.md
  - docs/roadmap/issue-AR-327-replay-codex-delivery-receipts-across-append-only-completion.md
  - docs/decisions/0190-bind-codex-receipt-replay-to-an-exact-append-only-prefix.md
  - docs/roadmap/handoffs/issue-AR-297.md
  - agency_runtime/core/canary_backends.py
  - agency_runtime/core/child_delivery_evidence.py
  - agency_runtime/core/store/evidence.py
  - tests/test_canary_activation_snapshot.py
  - docs/worklog/README.md
supersedes: []
superseded_by: null
id: ADR-0189
type: decision
deciders: [maintainers]
---

# ADR-0189: Admit only accepted terminal Codex parents for post-return collection

## Context

The exact rebuilt AR-297 Codex transaction proved the complete native child,
host-authored delivery, dispatch, wait, header, and first-pass accepted
finalization. Current-profile attestation still failed because the safe backend
collects its independently parsed child rollout only after `codex exec` returns,
while the shared restricted-parent resolver deliberately admitted only a live
run. By collection time the accepted terminal commit had made that exact parent
invisible.

Hooks need the live-only rule: a terminal parent must never authorize another
child start, stop, spawn reconciliation, or delivery write. The post-return
backend has the opposite lifecycle requirement, but Store presence or a generic
completed status alone cannot substitute for the authoritative finalization or
host artifact required by ADR-0156 and ADR-0179.

## Decision

The restricted Codex parent resolver remains live-only by default. It gains one
explicit, exclusive `accepted_terminal` mode for the safe backend's bounded
post-return host-artifact collector. That mode never falls back to a live run.

An accepted terminal parent must retain exactly one accepted activation-canary
route and one ready Codex run for the supplied session and trace. The run must
be `completed`, have a valid end timestamp, and bind one terminal finalization.
The canonical snapshot must contain exactly one finalization whose identifier
matches that binding, host is Codex, action is `accept`, missing list is empty,
terminal status is `completed`, response identity is a canonical SHA-256, and
creation timestamp equals the run's end timestamp. Canonical bounded run
metadata must contain no pending interaction or authorization. A closed run
without a binding, a non-accept action, missing evidence, multiple finalization
events, malformed metadata, or any active/terminal ambiguity fails closed.

Only `_collect_restricted_codex_canary_host_delivery` requests this mode. Hook
collection and every hook-side route caller omit it and therefore retain the
existing live-only contract. After parent resolution, all existing requirements
still apply: one inference-owned native-child route and immutable delivery
receipt, the host-authenticated child UUID, one owner-trusted canonical rollout,
complete pre-speech v6 card delivery, and both file and event timestamps inside
the measured invocation window. Terminal lookup locates evidence; it neither
creates nor upgrades that evidence.

## Consequences

The safe backend can collect the exact child artifact after a successful Codex
process has finalized, without reopening the parent or widening hook authority.
Rejected, continued, pending, ambiguous, stale, ordinary, or artifact-less
transactions remain unable to produce a sealed host-delivery proof.

The accepted-terminal contract is deliberately coupled to the current
first-pass canary lifecycle. If Codex or Agency introduces multiple legitimate
finalization events, pending accepted outcomes, or a different terminal status,
the canary fails until that new lifecycle receives its own review and evidence.

## Alternatives

Collecting before Codex returned was rejected because the canonical child
artifact and terminal host topology may still be incomplete. Reusing the live
resolver after return was rejected by the exact failure. Allowing terminal
parents in the default resolver was rejected because it would widen every hook
caller. Trusting any completed run, Store delivery row, or parent prose was
rejected because none proves an authoritative accept or host-authored delivery.
