---
title: "Checkpoint ordinary harness diagnostics"
status: active
category: worklog
created: 2026-08-27
updated: 2026-08-27
tags: [ar-297, codex, claude, openclaw, unattended, containers]
related:
  - docs/roadmap/issue-AR-297-complete-unattended-container-bootstrap.md
  - docs/roadmap/handoffs/issue-AR-297.md
  - docs/decisions/0173-complete-production-container-installation-with-managed-activation.md
  - docs/decisions/0181-use-litellm-aliases-as-host-inference-control-plane.md
supersedes: []
superseded_by: null
type: worklog
commit: 3fdb42185aa6ef65a672627a5ef3fcf58eebfb7b
short: 3fdb4218
date: 2026-08-27
pr: https://github.com/Holeshot-Software-LLC/agency-runtime/pull/337
related_issues:
  - docs/roadmap/issue-AR-297-complete-unattended-container-bootstrap.md
---

# Worklog detail: Checkpoint ordinary harness diagnostics

## Purpose

Preserve the first later ordinary Claude, OpenClaw, and Codex attempts with
exact native artifacts, Store correlations, and workforce-prompt visibility,
without promoting native process success over Agency's terminal policy.

## Approach

Each exact production-install container ran its normal unattended CLI with the
same self-contained read-only accessibility task. Agency credentials existed
only in process memory. No model override, activation bypass, foreign-policy
mutation, or Jina route was used. Native databases were backed up through
SQLite and native streams, sessions, and trajectories were copied into
owner-private evidence before content-minimized receipts were generated.

Claude R2 restored the current credential from the same approved read-only
host bind and injected the authenticated LiteLLM key. OpenClaw used its
corrected stable native alias with thinking off. Codex used ChatGPT auth, an
empty dedicated Git worktree, and the read-only sandbox under the persistent
managed-hook policy.

## Challenges encountered

Claude's installed hooks completed accepted routing and injected the exact
card, but its first-party OAuth session was expired and could not refresh.
OpenClaw completed natively but its approved 14B generation route returned the
exact empty object `{}`. Codex completed after choosing an opaque collaboration
child; Agency correctly refused the response because `evidence_verification`
was missing. These are three distinct terminal boundaries, not one generic
host failure.

## Decisions and alternatives

No unchanged Claude third attempt was run, and neither OpenClaw nor Hermes was
silently moved to another model. The owner interview remains authoritative for
both replacement aliases and any harness-auth change. Codex needs no config or
auth change; its next bounded attempt will explicitly require direct parent
analysis with no delegation or tools.

## Verification

- Claude native/Store receipts `c5c3b811...b54f` and
  `ef24801d...b6fb` prove all five Agency routes and one exact 3,227-byte card.
- OpenClaw native/Store receipts `0e4ecc3d...c53` and
  `6bf28dbe...367b` bind exit 0, a quick-checked native database, one exact
  card in the 7,591-byte prompt, and the terminal `response_invalid` row.
- Codex native/Store receipts `a18f2b10...71ed` and
  `06dcfe2f...e3e` bind its no-bypass read-only turn, exact parent/child card
  visibility, five Agency routes, and withheld finalization.
- End telemetry `63bf6e3a...beda` reports 45.6 percent remaining and requires
  this checkpoint before another live evaluation.
- Metadata, policy availability, worklog consistency, documentation validation
  for 909 Markdown files, and diff check all exit 0.

## Follow-ups

- Run direct-only Codex R2 after this ledger pair.
- Refresh the same Claude subscription login, then require accepted Claude
  finalization without changing its auth method.
- Interview the owner for the Hermes and OpenClaw replacement LiteLLM aliases.
- Continue exact host/dashboard proof, named gates, and final teardown.
