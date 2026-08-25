---
title: "Worklog detail: carry OpenClaw preflight model through final gates"
status: active
category: worklog
created: 2026-08-23
updated: 2026-08-23
tags: [openclaw, finalization, correlation, evidence]
related:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-264-compile-actionable-contractor-execution-profiles.md
  - docs/roadmap/issue-AR-279-deliver-openclaw-finalizer-results.md
  - docs/decisions/0167-refresh-openclaw-headers-through-awaited-tool-results.md
supersedes: []
superseded_by: null
type: worklog
commit: 71cb09751bc3b1f81cf4e0312765c616c305780c
short: 71cb0975
date: 2026-08-23
pr: null
related_issues:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-264-compile-actionable-contractor-execution-profiles.md
  - docs/roadmap/issue-AR-279-deliver-openclaw-finalizer-results.md
---

# Worklog detail: carry OpenClaw preflight model through final gates

## Purpose

Repair a live OpenClaw turn that authored the exact requested-alias status
header but was correctly withheld because OpenClaw omitted its local requested
model identifier from both final-hook contexts. Preserve the requested alias as
routing context without promoting it to an answering-model claim.

## Approach

Store the bounded preflight model identifier beside the generated plugin's
existing session/run preflight context. Reuse that value only when a final hook
does not supply a model, pass it to both pre-verification and outbound
revalidation, and delete it at the final payload gate. Existing expiry,
entry-count, byte-size, and runtime-disable clearing controls remain unchanged.

A focused generated-plugin regression supplies `task-general` at
`before_prompt_build`, omits it from the two final contexts exactly as the
installed OpenClaw version does, and requires both Agency bridge calls to
receive the correlated value.

## Challenges encountered

The fifth Telegram attempt completed six native model calls and tool work and
authored a 1274-character response, but queued no reply. It also produced zero
model receipts, proving the preceding alias-only telemetry repair worked.
Correlation isolated the remaining rejection to OpenClaw providing `modelId`
at preflight but omitting it at finalization.

The local `apply_patch` helper and ordinary sandbox commands remained
unavailable because the box could not create the sandbox loopback namespace.
Exact bounded replacements were used only after the helper failed, and every
resulting diff was inspected.

## Decisions and alternatives

The state is scoped to the generated OpenClaw plugin and the existing
session/run key. Shared finalization policy, other adapters, OpenClaw
source/configuration, native or Agency model routing, direct sending, response
rewrites, and correction passes were not changed. Treating the requested alias
as the answering model was rejected.

## Verification

- Expected-red: generated-plugin lifecycle regression exited 17 before the
  repair because pre-verification received an empty model.
- Focused OpenClaw adapter, security, registration, and native-installer slice:
  90 passed, 1 skipped, 148 deselected.
- Documentation metadata, policy availability, worklog consistency, and
  documentation validation passed.
- Repository-wide Ruff check and format check passed for 682 files.
- `git diff --check` passed.

## Follow-ups

Install Agency Runtime only into natively stopped OpenClaw from this clean
checkpoint, restart OpenClaw natively, verify config/plugin/channel/Store
invariants, and collect a genuinely fresh Telegram status response before skill
or substantive proof. Hermes and protected hosts remain untouched. Tracker
creation remains pending separate authorization.
