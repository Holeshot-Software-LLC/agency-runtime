---
title: "Bind Codex canary children through host-authored lineage"
status: active
category: worklog
created: 2026-08-27
updated: 2026-08-27
tags: [codex, canary, hooks, lineage, security, artifacts]
related:
  - docs/roadmap/issue-AR-297-complete-unattended-container-bootstrap.md
  - docs/roadmap/issue-AR-322-bind-codex-child-session-to-canary-parent.md
  - docs/roadmap/issue-AR-324-bind-codex-canary-child-through-host-lineage.md
  - docs/decisions/0156-host-artifacts-prove-native-child-delivery.md
  - docs/decisions/0179-admit-exact-codex-canary-delivery-at-subagent-start.md
  - docs/decisions/0187-bind-codex-canary-child-through-host-authored-lineage.md
  - agency_runtime/adapters/hooks.py
  - agency_runtime/core/child_delivery_evidence.py
supersedes: []
superseded_by: null
type: worklog
commit: 66b889a27fc51c0b4681469ce1624e2302dce4a2
short: 66b889a2
date: 2026-08-27
pr: null
related_issues:
  - docs/roadmap/issue-AR-297-complete-unattended-container-bootstrap.md
  - docs/roadmap/issue-AR-322-bind-codex-child-session-to-canary-parent.md
  - docs/roadmap/issue-AR-324-bind-codex-canary-child-through-host-lineage.md
---

# Worklog detail: Bind Codex canary children through host-authored lineage

## Purpose

Repair the exact no-bypass Codex production-container canary after a rebuilt
transaction proved that the correct request digest and accepted parent route
still did not reach the independently started child hook session. Preserve the
existing unstaffed fallback and every separate delivery, consumption, and
finalization gate.

## Approach

The restricted child hook now reads only the leading host-authored
`session_meta` record at the exact Codex `0.149.1` child rollout path. A
bounded, duplicate-rejecting, link-resistant owner-integrity reader pins the
canonical UUIDv7 child, version, origin, MultiAgent V2 shape, depth one,
no-inheritance history, child timestamps, agent metadata, and three agreeing
parent UUID fields. `SubagentStart` uses `transcript_path`; `SubagentStop` uses
`agent_transcript_path` because Codex separately exposes the parent transcript
as the stop event's ordinary transcript.

The host-authored parent UUID scopes one open trace and the complete accepted,
ready, nonterminal fixed-unit Store route. A request digest, when present, must
match that same route and can never choose a parent globally. Missing canary
mode or any artifact, lineage, route, run, or digest disagreement fails closed.

## Challenges encountered

The child exited successfully, which initially left model behavior, request
hashing, and delivery parsing plausible. Retained parent and child rollouts plus
the Store instead showed zero child routes and a generic identity. Official
tagged Codex source then established two relevant facts: each hook session
snapshots its own environment, while the child rollout independently records
the parent in three fields. The exact retained rollout supplied the closed
schema and causal UUID/timestamp relationships used by the reader.

## Decisions and alternatives

[ADR-0187](../decisions/0187-bind-codex-canary-child-through-host-authored-lineage.md)
supersedes the digest-inheritance join from ADR-0186. Selecting the globally
sole open run, trusting a successful child result, parsing opaque assignment
text, or treating Store presence as delivery proof remain rejected. Lineage
only recovers a parent; inference selection, host-written v6 delivery, one-use
consumption, response evidence, and attestation remain independent gates.

## Verification

- The focused warning-strict artifact, snapshot, and activation set passes
  137/137.
- The expanded Codex canary, artifact, Store-file-trust, and turn-boundary set
  passes 259/259 with `-W error`.
- Ruff check and format checks pass for the four changed Python/test files.
- Metadata, policy availability, worklog generation precheck, documentation
  validation for 889 Markdown files, and `git diff --check` pass before the
  substantive checkpoint; the following ledger commit restores Git parity.

## Follow-ups

- Rebuild exact artifacts and images from the clean ledger, then run one fresh
  no-bypass Codex production-container install under
  [AR-324](../roadmap/issue-AR-324-bind-codex-canary-child-through-host-lineage.md).
- Continue the remaining four-harness, ordinary-process, host/dashboard, gate,
  and teardown work under
  [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md).
- Tracker creation remains prohibited until the owner explicitly authorizes it.
