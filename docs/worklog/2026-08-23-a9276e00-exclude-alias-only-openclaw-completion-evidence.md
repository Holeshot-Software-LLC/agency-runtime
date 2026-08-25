---
title: "Worklog detail: exclude alias-only OpenClaw completion evidence"
status: active
category: worklog
created: 2026-08-23
updated: 2026-08-23
tags: [openclaw, finalization, evidence, litellm]
related:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-264-compile-actionable-contractor-execution-profiles.md
  - docs/roadmap/issue-AR-279-deliver-openclaw-finalizer-results.md
  - docs/decisions/0167-refresh-openclaw-headers-through-awaited-tool-results.md
supersedes: []
superseded_by: null
type: worklog
commit: a9276e00d1dc6862fb0f93085069c4fd5ff27ce9
short: a9276e00
date: 2026-08-23
pr: null
related_issues:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-264-compile-actionable-contractor-execution-profiles.md
  - docs/roadmap/issue-AR-279-deliver-openclaw-finalizer-results.md
---

# Worklog detail: exclude alias-only OpenClaw completion evidence

## Purpose

Repair a live OpenClaw turn that authored a complete Store-backed natural
response but was correctly withheld when alias-only model telemetry changed the
authoritative header after response authorship. Keep finalization fail-closed
and avoid claiming the requested LiteLLM alias as the answering model.

## Approach

At the OpenClaw bridge boundary, decline only `model_call_ended` observations
identified as `openclaw-litellm-router` when both resolved provider and
resolved model are absent. Such an event proves only the requested alias and
does not add actual-model evidence. Genuine resolved-model telemetry continues
through the existing receipt path unchanged.

A focused regression compares the authoritative model header before and after
one alias-only event. It requires the requested-alias line to remain stable and
requires no Store model receipt from that non-evidence event.

## Challenges encountered

The fourth Telegram attempt reached OpenClaw, completed three successful native
model calls and tool work, and produced a 665-character response, yet queued no
reply. Correlation showed finalization rejected only
`actual_model_selected`: three unavailable receipts arrived between header
authorship and validation. The first test invocation also hit the repository's
intentional trusted-namespace guard under the ambient umask; the expected-red
was then retained under a private mode-700 root with process umask 0077.

The local `apply_patch` helper and ordinary sandbox commands were unavailable
because the box could not create the sandbox loopback namespace, so exact
bounded replacements were used and every resulting diff was inspected.

## Decisions and alternatives

The change is OpenClaw-only. Shared header policy, other adapters, OpenClaw
source/configuration, native or Agency model routing, direct sends, response
rewrites, correction passes, and outbound authorization were not changed.
Persisting the alias as a resolved model was rejected because it would turn a
router/model-group name into a false answering-model claim.

## Verification

- Expected-red: focused regression failed on the persisted alias-only receipt.
- Focused OpenClaw adapter, middleware, and finalization slice: 31 passed, 1
  skipped.
- Cross-harness model-receipt parity slice: 6 passed.
- Documentation metadata, policy availability, worklog consistency, and
  documentation validation passed.
- Repository-wide Ruff check and format check passed for 682 files.
- `git diff --check` passed.

## Follow-ups

Reinstall Agency Runtime only into natively stopped OpenClaw from this clean
checkpoint, restart OpenClaw natively, and collect a genuinely new Telegram
status result before skill or substantive proof. Hermes and protected hosts
remain untouched. Tracker creation remains pending separate authorization.
