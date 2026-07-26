---
title: "AR-128: Seal model-facing control authority"
status: open
category: roadmap
created: 2026-07-26
updated: 2026-07-26
tags: [security, operations, dashboard, mcp, controls]
related:
  - docs/THREAT_MODEL.md
  - docs/decisions/0090-model-facing-control-paths-are-read-only.md
  - docs/decisions/0096-require-operator-presence-for-persistent-controls.md
  - docs/roadmap/issue-AR-143-require-operator-presence-for-controls.md
  - agency_runtime/core/dashboard_runtime.py
  - agency_runtime/cli/agent_control_broker.py
  - agency_runtime/server/mcp.py
supersedes: []
superseded_by: null
type: issue
epic: security
issue_id: AR-128
priority: p0
tracker_url: null
depends_on: []
blocks: [AR-143]
---

# AR-128: Seal model-facing control authority

## Problem

Restricted host hooks and MCP clients are in the threat model as potentially
compromised actors, but they can reach authenticated dashboard mutations using
predictable confirmation text. Possession of the model-facing broker capability
therefore acts as mutation authority rather than read authority.

## Current state

The loopback, origin, token, CAS, and response-validation controls prevent an
unrelated remote caller and stale writes. They do not distinguish a human
gesture from a compromised model, tool result, hook, or MCP client that already
holds the broker capability. The agent-control client also validates the active
Store path without proving desired Store identity and restart state.

## Approach

Make every broker capability issued to model-facing processes read-only. Keep
mutations on the owner-authenticated dashboard UI or an explicitly invoked
normal-user CLI boundary. Remove model-callable host mutation tools, preserve
read-only status tools, centralize exact active/desired/restart Store identity
validation, and retain CAS at the human mutation boundary.

## Dependencies

ADR-0090 governs the authority change and supersedes the older restricted-token
mutation decisions while retaining their useful read-only brokerage controls.

## Acceptance

- Model-facing broker tokens cannot reach any mutating route.
- MCP exposes no host, agent, or runtime mutation tool.
- Human dashboard and normal-user CLI mutations remain generation checked.
- Every Store-backed broker response proves active path, desired path, and
  `store_restart_required=false`.
- Adversarial protocol tests cover every formerly reachable mutation.

## Implementation evidence

The MCP registry, generated skill, restricted broker, and restricted CLI
fallbacks are now read-only. MCP bounds derive from canonical host and Store
identifier constants, Store-backed broker responses prove active/desired/restart
identity, and focused plus combined protocol tests pass.

AR-128 remains open because the owner dashboard is model-callable through the
in-app Browser. AR-143 and ADR-0096 own the newly reproduced user-presence gap;
the existing modal and bearer cannot be counted as proof of operator intent.
