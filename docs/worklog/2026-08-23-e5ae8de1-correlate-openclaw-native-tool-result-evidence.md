---
title: "Worklog detail: correlate OpenClaw native tool result evidence"
status: active
category: worklog
created: 2026-08-23
updated: 2026-08-23
tags: [openclaw, skills, middleware, correlation, evidence]
related:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-264-compile-actionable-contractor-execution-profiles.md
  - docs/roadmap/issue-AR-275-record-openclaw-native-skill-reads.md
  - docs/roadmap/issue-AR-279-deliver-openclaw-finalizer-results.md
  - docs/decisions/0167-authorize-openclaw-native-skill-reads-from-inventory.md
  - docs/decisions/0168-refresh-openclaw-headers-through-awaited-tool-results.md
supersedes: []
superseded_by: null
type: worklog
commit: e5ae8de1e278e2f6fcb40af818663c42186f7b42
short: e5ae8de1
date: 2026-08-23
pr: null
related_issues:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-264-compile-actionable-contractor-execution-profiles.md
  - docs/roadmap/issue-AR-275-record-openclaw-native-skill-reads.md
  - docs/roadmap/issue-AR-279-deliver-openclaw-finalizer-results.md
---

# Worklog detail: correlate OpenClaw native tool result evidence

## Purpose

Repair the exact OpenClaw lifecycle gap that delivered a successful
`task-agency-router` workforce turn and an inventory-authorized native skill
read, yet recorded no Store skill row because the awaited middleware callback
had no session/run correlation.

## Approach

Capture the host-authoritative session and run from OpenClaw's supported
`before_tool_call` hook under the native `toolCallId`. Consume that correlation
once in Agency's awaited tool-result middleware before calling the bridge.
Bound the state by ten-minute expiry and 128 entries, clear it when Agency is
disabled, reject oversized identities, and make collision ambiguity sticky and
fail closed. Existing middleware context remains a compatibility fallback when
a harness supplies it.

## Challenges encountered

The installed 2026.7.1 types advertise optional middleware context identities,
but its OpenClaw runtime factory constructs the middleware context with only
`runtime=openclaw`. Its lower-level tool-result event still carries the exact
arguments and call ID. The previous generated test invented session/run fields,
so it did not model the live host. A replay against an online Store backup
proved the Agency bridge records the authorized skill when given an open trace
and valid correlation.

## Decisions and alternatives

A process-global "latest turn" fallback was rejected because concurrent turns
could cross-bind evidence. Exact tool-call correlation is one-use; ambiguous
ID reuse remains unrecorded. No OpenClaw source or configuration, shared Agency
policy, inference route, direct delivery path, response rewrite, or protected
host adapter changed.

## Verification

- Expected-red: the installed-contract regression exited 245 because no
  `before_tool_call` correlation hook existed.
- Focused OpenClaw installer, dispatch, inference-profile, final-header, Store,
  and routing slice: 374 passed, 1 skipped.
- Documentation metadata, worklog consistency, and documentation validation
  passed. Policy availability passed with explicit checkout module discovery.
- Repository-wide Ruff check and format check passed for 682 files.
- `git diff --check` passed.

## Follow-ups

Install Agency Runtime only into natively stopped OpenClaw from the clean
checkpoint, restart OpenClaw natively, and use a fresh session with a genuinely
different eligible skill. If Store/header evidence passes, run the exact
non-mutating restart-safety request and finalize the OpenClaw bundle. Hermes and
protected hosts remain untouched. Tracker creation remains separately
authorized.
