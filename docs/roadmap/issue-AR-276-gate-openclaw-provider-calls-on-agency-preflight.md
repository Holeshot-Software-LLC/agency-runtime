---
title: "Gate OpenClaw provider calls on Agency preflight"
status: in_progress
category: roadmap
created: 2026-08-22
updated: 2026-08-22
tags: [openclaw, preflight, safety, reliability]
related:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-275-preserve-planner-repair-diagnostics.md
  - docs/roadmap/handoffs/issue-AR-119.md
  - docs/roadmap/AR-119-openclaw-hermes-verification-packet.md
  - agency_runtime/core/installer_payload_openclaw.py
  - tests/test_security_turn_boundaries.py
supersedes: []
superseded_by: null
type: issue
epic: reliability
issue_id: AR-276
priority: p0
tracker_url: null
depends_on: [AR-275]
blocks: [AR-119]
---

# AR-276: Gate OpenClaw provider calls on Agency preflight

## Problem

The audited OpenClaw 2026.7.1 contract gives `before_agent_run` a
prompt-bearing, fail-closed input decision. Agency used that gate only to read
runtime control and streaming safety. It ran actual workforce preflight later
in `before_prompt_build`, whose result can only mutate prompt context and whose
exceptions are logged and ignored by OpenClaw.

When Agency returned no context after a terminal routing failure, the prompt
hook returned no mutation and OpenClaw started its native provider anyway.
This spent host-model tokens on an ungoverned turn and could never produce a
valid Agency header or finalization.

## Current state

Fresh session `44c5c168-b8db-4a3e-8a31-131251199b27` / Agency trace
`8b9b539d-2005-42fe-b38a-9598ade34367` failed workforce preflight at
`2026-08-22T13:30:16.366000+00:00`. Receipt
`b46c36d8-7cd3-418c-bc32-495e72ce5d98` records two rejected LiteLLM planner
attempts and no protected fallback.

The native receipt then reported `providerStarted: true`, provider
`litellm`, model `task-general`, 58 tool calls, and a 300-second timeout.
No Agency header or accepted finalization exists. The complete failure artifact
is retained at `/tmp/ar275-openclaw-substantive-turn.json`.

The focused generated-plugin regression failed before repair at exit 203:
`before_agent_run` made no preflight bridge call. It now passes with the
planner and input-gate slice (154 tests) and the affected installer/adapter
slice (65 tests).

Commits `a0ff74d4` / `77bfd2ae` are installed as Agency-only install
`ba074210-c785-4d61-a014-c2f86dfdb571`. OpenClaw is RPC-green and the plugin
is enabled, activated, loaded with ten hooks, and exposes preflight in
`before_agent_run` at priority 1000. Native model/provider/channel/alias
configuration is unchanged; only `/meta/lastTouchedAt` differs.

Three distinct Agency-only routes did not reach admission, so no native turn
was sent after reinstall. This prevents another token-heavy host fallback but
leaves live input-gate blocking and accepted header/finalization unproven.
The OpenClaw-only soft bypass dry run passed; applying it was rejected pending
explicit owner approval because it disables Agency enforcement for that host.
Telegram and Slack themselves remain connected and probe-green.

## Approach

Run the existing exact Agency preflight call inside OpenClaw's
`before_agent_run` gate after runtime-control and final-only delivery checks.
Block with a bounded user-facing error when the bridge fails or does not return
a complete context.

Cache only the successful bounded context, keyed by exact session and run, for
the immediately following `before_prompt_build` injection. Bound the cache by
count and TTL, clear it when Agency is disabled, and remove its entry during
finalization. The prompt hook performs no second provider-backed preflight.

This changes only the generated Agency plugin payload. It does not modify
OpenClaw's native model, provider list, channels, aliases, or configuration.

## Dependencies

- AR-275 strict planner diagnosis and repair.
- Installed OpenClaw 2026.7.1 fail-closed `before_agent_run` contract.
- Existing Store preflight/finalization and final-only outbound enforcement.

## Acceptance

- [x] Exact failed live turn and native provider-start receipt are retained.
- [x] Expected-red proves preflight did not run in the blocking input gate.
- [x] Successful preflight runs once, then its bounded exact context reaches prompt build.
- [x] Missing or failed preflight returns an input-gate block before model execution.
- [x] Cache is exact-session/run scoped, bounded, expiring, and cleared on disable/finalization.
- [x] Focused and affected local tests pass.
- [x] Clean local substantive/ledger commits are `a0ff74d4` / `77bfd2ae`.
- [x] Agency-only reinstall preserves native OpenClaw configuration except its timestamp metadata.
- [ ] Fresh changed turn proves no native provider starts after preflight rejection.
- [ ] Fresh accepted turn proves Store routing, header delivery, and finalization.
- [ ] Tracker creation remains pending separate authorization.
