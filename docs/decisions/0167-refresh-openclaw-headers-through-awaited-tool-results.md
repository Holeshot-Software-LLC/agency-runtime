---
title: "Refresh OpenClaw headers through awaited tool results"
status: accepted
category: decisions
created: 2026-08-23
updated: 2026-08-23
tags: [openclaw, finalization, headers, tool-results, host-integration]
related:
  - docs/roadmap/issue-AR-279-deliver-openclaw-finalizer-results.md
  - docs/roadmap/handoffs/issue-AR-119.md
  - docs/roadmap/handoffs/issue-AR-264.md
  - docs/decisions/0049-openclaw-final-only-full-payload-delivery.md
  - docs/decisions/0120-construct-first-pass-evidence-headers.md
  - agency_runtime/core/installer_payload_openclaw.py
  - agency_runtime/adapters/openclaw/node_bridge.py
  - tests/test_security_turn_boundaries.py
  - tests/test_adapter_parity.py
  - tests/test_native_installer.py
supersedes: []
superseded_by: null
id: ADR-0167
type: decision
deciders: [maintainers]
---

# ADR-0167: Refresh OpenClaw headers through awaited tool results

## Context

OpenClaw 2026.7.1-2 does not promote a plugin tool result into the host-owned
final response. A model can receive an accepted Agency finalizer result and
then emit exact `NO_REPLY`; OpenClaw removes that sentinel before the outbound
payload hooks, leaving no channel response. Marking the tool terminal does not
solve this: OpenClaw classifies a final assistant event ending in tool use as a
non-deliverable terminal turn unless the host itself records an explicit
terminal delivery.

A correction model pass, direct channel send, host-source change, or post-model
rewrite would violate the existing first-pass and full-payload boundaries.
OpenClaw does expose an awaited `registerAgentToolResultMiddleware` surface.
That middleware runs after a native tool result is available and before the
model continues, so Agency can persist the observation and provide current
Store evidence without racing the next model step.

## Decision

For OpenClaw only, construct the first visible response naturally from exact
Store-backed snapshots instead of exposing `agency_finalize` as a native tool.
Preflight supplies an initial five-line snapshot. The generated plugin registers
one awaited tool-result middleware scoped to runtime `openclaw`; it records each
tool observation through `post_tool_call`, obtains an updated snapshot from the
same correlated Store turn, preserves the native tool result, and appends that
snapshot as context for the next model step. The newest snapshot supersedes all
earlier snapshots for the turn.

If Agency is disabled or cannot produce an exact correlated snapshot, the
middleware returns the original host result unchanged and never fabricates
header values. The model is instructed to emit one natural final response that
begins byte-for-byte with the newest snapshot, never call a finalizer tool, and
never emit `NO_REPLY`. `before_agent_finalize` still validates the first natural
response, and ADR-0049's final reply-payload gate still commits and authorizes
the complete outbound envelope. There is no correction pass.

The OpenClaw bundle manifest declares
`agentToolResultMiddleware: [openclaw]`. Smoke validation and native runtime
inspection require that contract in addition to the typed hooks; a loaded
plugin without it remains registration-unproven and is disabled. The internal
bridge finalizer action remains readable for compatibility and historical
evidence, but the generated OpenClaw plugin no longer exposes the tool.

Hermes retains its existing local-finalizer path. Codex, Claude, ZCode, host
model configuration, and harness-scoped inference profiles are unchanged.

## Consequences

- OpenClaw no longer depends on a second model action after a finalizer tool
  result, removing the observed `NO_REPLY` failure mechanism.
- Tool-derived skill and specialist evidence reaches the model only after the
  Store observation completes, so the final header can remain exact without a
  racy fire-and-forget hook.
- A missing middleware contract fails installation proof instead of producing a
  falsely mature integration.
- The model still authors the first natural response. Header or evidence drift
  remains terminally invalid and cannot be repaired into success.
- The change is host-specific; it establishes no live delivery, child-delivery,
  or AR-119 matrix claim until fresh host evidence exists.

## Alternatives

- Keep `agency_finalize` and ask the model to copy its result. Rejected because
  three retained Telegram attempts prove tool-result acceptance is not channel
  delivery and can end in exact `NO_REPLY`.
- Terminate the turn from the finalizer tool. Rejected because OpenClaw treats a
  last assistant tool-use event without explicit host delivery as
  non-deliverable.
- Send the accepted text directly from Agency. Rejected because that bypasses
  host-owned channel delivery and can duplicate or escape the outbound seal.
- Use `before_agent_finalize` to revise or replace the draft. Rejected because
  the supported surface requests another model pass and cannot supply the final
  payload.
- Apply the same mechanism to every harness now. Rejected because each harness
  has a different native lifecycle; Hermes and the already-proven hosts must
  not change without independent evidence.
