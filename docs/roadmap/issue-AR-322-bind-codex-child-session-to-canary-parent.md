---
title: "AR-322: Bind Codex child sessions to the exact canary parent"
status: in_progress
category: roadmap
created: 2026-08-27
updated: 2026-08-27
tags: [bug, codex, canary, hooks, native-child, security]
related:
  - docs/roadmap/issue-AR-297-complete-unattended-container-bootstrap.md
  - docs/roadmap/issue-AR-310-require-managed-codex-canary-store.md
  - docs/roadmap/issue-AR-314-bind-codex-default-canary-role.md
  - docs/roadmap/handoffs/issue-AR-297.md
  - docs/decisions/0179-admit-exact-codex-canary-delivery-at-subagent-start.md
  - docs/decisions/0186-bind-codex-child-session-with-canary-request-digest.md
  - docs/decisions/0187-bind-codex-canary-child-through-host-authored-lineage.md
  - docs/roadmap/issue-AR-324-bind-codex-canary-child-through-host-lineage.md
  - agency_runtime/adapters/hooks.py
  - agency_runtime/core/canary_backends.py
  - agency_runtime/core/codex_activation_verification.py
  - agency_runtime/core/store/evidence.py
  - tests/test_canary_activation_snapshot.py
  - tests/test_codex_activation_verification.py
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: host-integrations
issue_id: AR-322
priority: p0
tracker_url: null
depends_on: [AR-310, AR-314]
blocks: [AR-297, AR-324]
---

# AR-322: Bind Codex child sessions to the exact canary parent

## Problem

Codex `rust-v0.149.1` sends the child's own session UUID as `session_id` in
`SubagentStart` and `SubagentStop`. Agency treated that field as the parent
session and therefore could not recover the already-accepted parent route.
The exact child completed successfully but received only the generic unstaffed
identity message, so no v6 workforce delivery or activation proof existed.

## Current state

- Stable LiteLLM alias proof `54a773f7...00d3` selects sole `code-reviewer`
  through the promoted schema-bound Mistral deployment.
- Fresh exact Codex install `d08883a7...7623` accepts parent route
  `6ca7be2e...0da7`, spawns child `01a04187...ac7e`, waits once for 300 seconds,
  and receives child exit 0 without timing out.
- Parent and child rollouts `16f4d5e2...2934` and `910538f1...6953` prove the
  child received only generic identity context. Store `d3471c9a...e2af` has no
  child parent-scope, captured-assignment, delivery-verification, or native-plan
  row for that child.
- The official `rust-v0.149.1` hook implementation constructs the lifecycle
  request from the child session while retaining the host-created child UUID as
  `agent_id`; an omitted explicit role still correctly reports `default`.
- Source checkpoint `a5c1ad53` implements the bounded repair; 99 focused
  warning-strict regressions pass.
- Clean ledger `c7f35dd5` canonical build, strict Twine, independent verifier,
  six image builds, and five-image label/version verification all exit 0.
  Wheel `23036c74...d68d`, sdist `09b85884...1a3b`, and image receipt
  `f1808c22...64674` bind the fresh candidate. Live proof remains pending.
  Fresh rebuilt production-container proof `999f3005...33269` exits 1: the
  parent digest and route agree, but the child still receives generic identity.
  AR-324 owns the replacement host-lineage join.
- Tracker creation is prohibited by the active AR-297 task.

## Approach

Project the SHA-256 digest of the exact nonce-bearing canary request into only
the restricted current-profile canary process. At a Codex child lifecycle hook,
require the supplied child `session_id` to equal `agent_id`, validate the
lowercase digest, and resolve the unique Store snapshot by host and digest.
Admit the parent only when the snapshot, run, route, fixed work-unit summary,
request fingerprint, status, and nonterminal state all match. Keep parent hooks
on their direct parent session/turn resolver and keep ordinary and product
processes free of this capability.

## Dependencies

- AR-310 owns the exact existing Store used by the managed canary.
- AR-314 owns the separate `agent_type=default` host-schema discriminator.
- ADR-0179 still requires host-authored v6 delivery and a one-use receipt;
  resolving a parent alone does not prove delivery.
- The nonce-bearing request is unique per invocation. A duplicate Store route
  for the same digest must remain ambiguous and fail closed.

## Acceptance

- [x] The exact backend projects a lowercase request digest only for restricted
      current-profile activation canaries, never ordinary/product processes.
- [x] Child hooks require `session_id == agent_id` and resolve exactly one
      active, ready, nonterminal parent route by the same Store fingerprint.
- [x] Missing, malformed, mismatched, unknown, or duplicate digests fail closed.
- [x] Parent `UserPromptSubmit` plan injection keeps its direct parent scope.
- [x] Focused warning-strict activation and snapshot regressions pass (99).
- [ ] A rebuilt fresh no-bypass Codex install proves v6 delivery, consumption,
      header, accepted finalization, Store correlation, and attestation.
- [ ] A same-repository tracker issue is created and linked after explicit
      authorization.
