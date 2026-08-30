---
title: "Accept the PreToolUse hook in the Codex bundle contract"
status: active
category: worklog
created: 2026-07-23
updated: 2026-07-23
tags: [worklog, smoke, codex, hooks, AR-119, green-main]
related:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-117-parallelize-pr-verification.md
  - docs/roadmap/issue-AR-116-bound-child-routing-and-oauth-model-selection.md
supersedes: []
superseded_by: null
type: worklog
commit: 10e3b4c
short: 10e3b4c
date: 2026-07-23
pr: null
related_issues:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-117-parallelize-pr-verification.md
  - docs/roadmap/issue-AR-116-bound-child-routing-and-oauth-model-selection.md
---

# Worklog detail: fix(smoke): accept the PreToolUse hook in the Codex bundle contract

## Purpose

After PR #129 merged, both artifact-smoke CI jobs (ubuntu-24.04 and
windows-2022) failed `agency smoke --all`, and ~17 marketplace-schema
test cases failed, all with
`RuntimeError: Codex bundle has an invalid hook event set`. This was the
highest-blast-radius failure on merged `main` and blocked the green-main
gate.

## Approach

Root cause: PR #129 intentionally added a `PreToolUse` hook event
(matcher `spawn_agent`) to the generated Codex bundle to bind the exact
Agency specialist to each native child. The event is wired end to end:

- `installer_payloads.codex_hooks` emits it
- `adapters/hooks` dispatches it to `_handle_native_child_pre_tool_use`
- the runtime `_CODEX_EVENTS` and CLI `_NATIVE_HOOK_EVENTS` lists include it
- the host guidance documents the installed PreToolUse hook

The smoke validator's `_CODEX_HOOK_EVENTS` constant in `core/smoke.py`
was not updated with that change, so it still demanded the pre-#129
seven-event set and rejected the now-eight-event bundle. This was a
contract-lag, not a production regression, so the fix aligns the
validator to the intended contract: add `PreToolUse` to the expected
event tuple.

The existing per-event shape checks already validate the `PreToolUse`
registration correctly because it is produced by the same `handler()`
factory as the other events (single registration, `timeout` int,
`type=="command"`, `async is False`, command tokens present, Windows
command starts with `& `), and the `matcher=="*"` requirement is gated
to `PostToolUse` only, so `PreToolUse`'s `spawn_agent` matcher is valid.

## Challenges encountered

- The failure surfaced identically across the marketplace-schema
  parametrized cases because the event-set check is the validator's
  first gate; every downstream message branch was unreachable until the
  set matched.
- Confirmed empirically that the bundle emits 8 events, the runtime
  accepts 10, the CLI canonical list includes PreToolUse, and only the
  smoke constant (7 events) was the outlier.

## Decisions and alternatives

- Align the validator constant to the new contract rather than reverting
  the production hook, because the PreToolUse specialist-binding is the
  intended AR-116/AR-119 native-child behavior.
- Rejected: dropping PreToolUse from the bundle. That would remove the
  native-child specialist binding, an intended feature.

## Verification

- `python -m pytest tests/test_smoke_coverage_complete.py tests/test_doctor.py -q -W error`
  -> **44 passed**.
- `agency smoke --json` -> **`passed: true`, `failed_count: 0`,
  `plugin_codex: pass`** (the exact runtime path the artifact-smoke CI
  job runs).
- `ruff check agency_runtime/core/smoke.py` -> clean.
- No other references to `_CODEX_HOOK_EVENTS` or the error message exist
  in the codebase, so the change is self-contained.

## Follow-ups

- This unblocks artifact smoke and the marketplace-schema cases. The
  remaining Phase 0 failures (routing `_RouteRequest` signature,
  workforce contract validation, store/schema fixes, dashboard/MCP/
  delegation-activation reconciliation) must still be resolved before
  merged `main` CI is fully green. Tracked under
  [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md) and
  [AR-117](../roadmap/issue-AR-117-parallelize-pr-verification.md).
