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

The owner later authorized changing only the LiteLLM alias target. A free local
30B coder target accepted the exact required substantive Agency-only route
across planner, recruiter, and critic with zero fallback. Fresh native status
run `341ec5f5-9343-499f-8a73-d0c6cb08426c` then reached Store preflight
`ready`, but OpenClaw injected zero runtime-context characters. Its normal
`task-general` model ran, used invented finalization correlation IDs, and
closed Store run `7daf7c70-c87b-4ed7-bf31-3e093bab73b5` as
`response_invalid`; no Agency header was delivered.

Installed OpenClaw 2026.7.1-2 requires non-bundled plugins to grant
`hooks.allowPromptInjection=true` before accepting `before_prompt_build`
prompt-mutation fields. Agency registration granted conversation access only.
The expected-red registration receipt is retained. Agency-only install
`18b2d5f7-a931-4606-8d6f-9e30937cfbcc` proved the permission without changing
native inference or channel configuration.

Fresh permission-enabled run `d343b0c0-68a9-4857-b8d3-41cd3125cd3a` still
reported zero runtime-context characters and delivered no Agency header.
Installed OpenClaw source then proved the lifecycle order is
`before_prompt_build` followed by `before_agent_run`, while Agency and its test
modeled the reverse. The corrected expected-red failed at exit 204 before the
implementation change and now passes with the full 46-test security-boundary
file plus focused installer/adapter slices of 36, 24, 1, and 46 cases.

Commits `d9a1a7ce` / `1a737ef8` implement and record the corrected order.
Agency-only install `1eeba99b-49a1-4db5-b561-9d985c30d29e` loaded that exact
checkout without reinstalling OpenClaw. Fresh status trace
`bf21e9a8-a9f0-442b-9d75-78dab94687d6` completed Store routing and accepted
finalization, and the native response delivered the exact five-line Agency
header. A changed nontrivial skill turn then hit the native hook budget and
returned `hook_block` before reply generation; it did not fall through to the
normal host model. The timeout and still-active Store run are retained and are
not promoted into successful inference evidence.

Credential-correct free-14B trace `2317d975-c960-4020-8755-f32308ffe94b`
then accepted all three inference stages within 37.768 seconds. Fresh native
trace `79abdac7-42f1-44e9-afad-bf5556df62aa` completed the exact Store route,
loaded `code-reviewer`, recorded skill `tmux`, accepted finalization, and
delivered the authoritative five-line inference header in 45.085 seconds.
No preflight bypass occurred: native `task-general` answered only after the
accepted preflight; no child, mutation, network action, or delegation ran.

## Approach

Run runtime control and the existing exact Agency preflight during
`before_prompt_build`, cache the successful bounded context by exact session
and run, and return it as `appendContext`. The later `before_agent_run` gate
rechecks runtime control and final-only delivery, then passes only when that
exact cached context exists. OpenClaw may ignore a prompt-hook exception, but
the input gate therefore still blocks before the model call.

This changes the generated Agency plugin payload and its plugin-owned native
registration permission only. Registration grants
`hooks.allowPromptInjection` with OpenClaw's supported config command.
Failure at that exact step rolls back through the existing final-only delivery
transaction. No native model, provider, fallback, channel, or alias setting
changes.

## Dependencies

- AR-275 strict planner diagnosis and repair.
- Installed OpenClaw 2026.7.1 fail-closed `before_agent_run` contract.
- Existing Store preflight/finalization and final-only outbound enforcement.

## Acceptance

- [x] Exact failed live turn and native provider-start receipt are retained.
- [x] Expected-red proves the installed host calls prompt build before the input gate.
- [x] Successful preflight runs once during prompt build and its bounded exact context is returned there.
- [x] Missing or failed preflight returns an input-gate block before model execution.
- [x] Cache is exact-session/run scoped, bounded, expiring, and cleared on disable/finalization.
- [x] Focused and affected local tests pass.
- [x] Clean local prompt-order substantive/ledger commits are `d9a1a7ce` / `1a737ef8`.
- [x] Agency-only reinstall preserves native OpenClaw configuration except its timestamp metadata.
- [x] Exact native failure proves Store preflight context was created but prompt mutation was not authorized.
- [x] Expected-red and focused tests cover the required prompt-injection permission and exact-step rollback.
- [ ] Fresh changed turn proves no native provider starts after preflight rejection.
- [x] Fresh accepted status turn proves Store routing, header delivery, and finalization.
- [x] Permission candidate was reinstalled Agency-only and proven from native config.
- [x] Prompt-build-order candidate is reinstalled Agency-only into stopped OpenClaw.
- [x] Fresh accepted nontrivial turn proves workforce routing without exceeding the native hook budget.
- [ ] Tracker creation remains pending separate authorization.
