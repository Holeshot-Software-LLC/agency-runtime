---
title: "Worklog detail: refresh OpenClaw headers through awaited tool results"
status: active
category: worklog
created: 2026-08-23
updated: 2026-08-23
tags: [openclaw, finalization, headers, tool-results]
related:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-264-compile-actionable-contractor-execution-profiles.md
  - docs/roadmap/issue-AR-279-deliver-openclaw-finalizer-results.md
  - docs/decisions/0168-refresh-openclaw-headers-through-awaited-tool-results.md
supersedes: []
superseded_by: null
type: worklog
commit: da184b4fc6170ff1bffcff8d827910e09b848f6a
short: da184b4f
date: 2026-08-23
pr: null
related_issues:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-264-compile-actionable-contractor-execution-profiles.md
  - docs/roadmap/issue-AR-279-deliver-openclaw-finalizer-results.md
---

# Worklog detail: refresh OpenClaw headers through awaited tool results

## Purpose

Repair OpenClaw Agency turns that completed a Store-backed finalizer tool call
but produced no Telegram response when the native model then emitted exact
`NO_REPLY`. Keep OpenClaw source, native model routing, Agency inference
routing, Hermes, and all proven hosts outside the change boundary.

## Approach

Remove the generated OpenClaw `agency_finalize` tool and use the host's awaited
tool-result middleware. Preflight supplies an initial exact Store-backed
five-line snapshot. After every native tool result, the middleware awaits Agency
observation, preserves the native result, and appends an updated exact snapshot
before the model continues. The existing first-pass final validation and
full-payload outbound authorization remain authoritative.

Declare and prove the OpenClaw
`contracts.agentToolResultMiddleware: [openclaw]` capability during smoke and
native registration inspection. A missing contract fails closed. ADR-0168
records why this is OpenClaw-only.

## Challenges encountered

The installed OpenClaw terminal classifier proved that ending on a tool-use event
without explicit host delivery is non-deliverable, ruling out a terminal-tool
handshake. Expected-red exit 232 captured the old exposed finalizer. Pytest first
created group-writable fixture parents under the machine's ambient umask and
triggered Agency's namespace guard; the unchanged tests were rerun under a
private mode-700 root and process umask 0077. A broader gate then found three
successful registration fixtures missing the newly required contract; only
those success fixtures were corrected, while an independent absent-contract
test retains the fail-closed behavior.

## Decisions and alternatives

ADR-0168 owns the host-specific decision. Direct channel send, a second model
pass, invalid-draft rewrite, OpenClaw source/configuration change, and applying
the mechanism to other harnesses were rejected. The internal bridge finalizer
action remains available for compatibility and historical evidence but is not
exposed by the generated OpenClaw plugin.

## Verification

- Expected-red exit 232 was retained before the implementation.
- OpenClaw security, adapter, and native-installer slice: 72 passed, 148
  deselected.
- Header, Store, inference-profile, registration, and OpenClaw policy slice:
  289 passed, 2 skipped.
- Documentation metadata, policy availability, worklog consistency, and
  documentation validation passed.
- Repository-wide Ruff check and format check passed for 682 files.
- `git diff --check` passed.

## Follow-ups

Install Agency Runtime only into a natively stopped OpenClaw gateway from this
clean checkpoint, restart OpenClaw natively, and collect fresh Telegram plus
post-live Store/config evidence under AR-279. Hermes and protected hosts remain
untouched. Tracker creation remains pending separate authorization.
