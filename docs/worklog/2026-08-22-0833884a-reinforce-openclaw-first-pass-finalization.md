---
title: "Reinforce OpenClaw first-pass finalization"
status: active
category: worklog
created: 2026-08-22
updated: 2026-08-22
tags: [openclaw, finalization, prompts, safety]
related:
  - docs/worklog/README.md
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-264-compile-actionable-contractor-execution-profiles.md
  - docs/roadmap/issue-AR-273-expose-openclaw-native-finalizer-tool.md
  - docs/roadmap/issue-AR-277-gate-openclaw-provider-calls-on-agency-preflight.md
  - docs/roadmap/issue-AR-278-keep-openclaw-finalization-first-pass.md
  - docs/decisions/0049-openclaw-final-only-full-payload-delivery.md
  - docs/decisions/0120-construct-first-pass-evidence-headers.md
supersedes: []
superseded_by: null
type: worklog
commit: 0833884a5b5a66293c7974dec3062755a0b10440
short: 0833884a
date: 2026-08-22
pr: null
related_issues:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-264-compile-actionable-contractor-execution-profiles.md
  - docs/roadmap/issue-AR-273-expose-openclaw-native-finalizer-tool.md
  - docs/roadmap/issue-AR-277-gate-openclaw-provider-calls-on-agency-preflight.md
  - docs/roadmap/issue-AR-278-keep-openclaw-finalization-first-pass.md
---

# Worklog detail: fix(openclaw): reinforce first-pass finalization

## Purpose

Keep a substantive OpenClaw turn from forgetting the registered Store-backed
finalizer after ordinary tool use, while preserving the first-invalid-response
terminal contract and final-only outbound seal.

## Approach

Make `agency_finalize` explicitly mandatory in its persistent native tool
guidelines whenever Agency preflight supplied current correlation. Repeat the
same requirement after every other tool call and at the end of the per-turn
Store context. The model must call the existing finalizer exactly once before
natural final output and emit its result byte-for-byte.

## Challenges encountered

The exact live request accepted Agency inference but the native host model
stopped without calling the finalizer. An initial bounded-revision candidate
passed focused tests, but review against ADR-0120 showed that it would revive a
rejected second model pass. It was removed before commit or installation. A
test-string escaping failure and one context-position assertion failure are
retained separately from the meaningful expected-red exit 219.

## Decisions and alternatives

Preserve ADR-0049 and ADR-0120 unchanged. Strengthen first-pass instructions
instead of enabling `action: revise`, rewriting an invalid response, relaxing
Store verification, or changing OpenClaw's native model/provider configuration.

## Verification

The meaningful regression failed before repair at exit 219. After repair, the
focused pair passes 2/2; the affected suites pass 47 security-boundary, 36
OpenClaw installer, and 24 OpenClaw adapter-parity tests. Focused Ruff
lint/format, metadata, policy-availability, worklog, documentation validation,
and `git diff --check` pass.

## Follow-ups

Install Agency only into stopped OpenClaw, run one genuinely changed fresh
substantive work unit, require first-pass finalization and exact Store/header
correlation, then take the post-live Store backup under
[AR-278](../roadmap/issue-AR-278-keep-openclaw-finalization-first-pass.md).
