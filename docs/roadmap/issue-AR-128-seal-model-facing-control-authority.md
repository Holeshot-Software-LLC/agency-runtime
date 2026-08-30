---
title: "AR-128: Seal model-facing control authority"
status: done
category: roadmap
created: 2026-07-26
updated: 2026-08-12
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

The original broker and Store-identity defects are repaired. MCP, generated
host, restricted CLI, and dashboard surfaces expose only bounded reads and
computations; every former dashboard mutation rejects without dispatch. The
separate absence of a positive OS-backed operator path is owned by AR-143.

## Approach

Make every broker capability issued to model-facing processes read-only. Remove
model-callable mutation tools and dashboard mutation clients, preserve read-only
status tools, and centralize exact active/desired/restart Store identity
validation. Leave any future positive CLI mutation behind AR-143's independent
OS-backed operator-presence boundary.

## Dependencies

ADR-0090 governs the authority change and supersedes the older restricted-token
mutation decisions while retaining their useful read-only brokerage controls.

## Acceptance

- [x] Model-facing broker tokens cannot reach any mutating route.
- [x] MCP exposes no host, agent, or runtime mutation tool.
- [x] No dashboard bearer can mutate; future positive CLI mutations remain
  generation checked behind genuine operator presence.
- [x] Every Store-backed broker response proves active path, desired path, and
  `store_restart_required=false`.
- [x] Adversarial protocol tests cover every formerly reachable mutation.

These checks preserve the 2026-07-25 contract as historical evidence. ADR-0117
later superseded the no-dashboard-bearer clause by recognizing the owner
dashboard bearer as equivalent owner authority while keeping hook, MCP, and
broker credentials read-only.

## Implementation evidence

The MCP registry, generated skill, restricted broker, restricted CLI fallbacks,
and owner dashboard are now read-only. MCP bounds derive from canonical host and
Store identifier constants, Store-backed broker responses prove
active/desired/restart identity, and focused plus combined protocol tests pass.
AR-128 is locally complete; AR-143 separately owns the deliberately unavailable
positive operator-presence path.
