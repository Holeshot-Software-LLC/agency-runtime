---
title: "Model-facing control paths are read-only"
status: superseded
category: decisions
created: 2026-07-26
updated: 2026-07-26
tags: [security, mcp, dashboard, controls, authority]
related:
  - docs/roadmap/issue-AR-128-seal-model-facing-control-authority.md
  - docs/decisions/0058-broker-restricted-windows-host-controls.md
  - docs/decisions/0059-broker-restricted-windows-agent-controls.md
  - docs/decisions/0060-restricted-windows-cli-read-and-fail-safe.md
  - docs/decisions/0061-validate-brokered-control-transition-receipts.md
  - docs/THREAT_MODEL.md
  - agency_runtime/core/dashboard_runtime.py
  - agency_runtime/server/mcp.py
supersedes:
  - docs/decisions/0058-broker-restricted-windows-host-controls.md
  - docs/decisions/0059-broker-restricted-windows-agent-controls.md
  - docs/decisions/0061-validate-brokered-control-transition-receipts.md
superseded_by: docs/decisions/0096-require-operator-presence-for-persistent-controls.md
id: ADR-0090
type: decision
deciders: [maintainers]
---

# ADR-0090: Model-facing control paths are read-only

## Context

The threat model treats a compromised model, tool result, host hook, or MCP
client as an attacker. Earlier decisions allowed an exactly identified
restricted Windows hook to broker persistent host and agent mutations through
the authenticated dashboard using public deterministic confirmation text and
CAS. Those controls prove service, identity, and freshness, but they do not
prove human intent. A caller already executing in the model-facing process can
read the generation and construct the published phrase.

## Decision

Capabilities delivered to MCP servers, generated hooks, and restricted
model-facing CLI processes are read-only. They may obtain bounded status,
selection, and evidence projections after exact identity checks. They cannot
mutate Agency master state, host controls, agent activation, configuration,
Store content, native lifecycle, or maintenance state.

Persistent mutations remain available through the owner-authenticated dashboard
UI and explicitly invoked normal-user CLI commands. Those human-facing paths
retain exact confirmation, generation CAS, locked identity rechecks, and
postcondition receipts. A future remote mutation surface would require a
short-lived, single-use user-presence capability bound to exact operation,
target, desired state, generation, and expiry; a static phrase is not such a
capability.

## Consequences

- Prompt injection cannot turn a model-facing broker token into persistent
  control authority.
- Restricted Windows model processes lose convenient host/agent mutations and
  must instruct the operator to use the dashboard or normal-user CLI.
- Read-only brokerage from ADR-0060 remains valid, but desired Store identity
  and restart state must be verified on every Store-backed response.
- ADR-0058, ADR-0059, and ADR-0061 are superseded because their brokered
  mutation authority is removed.

## Alternatives

- **Keep static confirmation plus CAS.** Rejected because it proves request
  shape and freshness, not the user's presence or intent.
- **Treat the local model process as trusted.** Rejected because it contradicts
  the repository threat model.
- **Mint a user-presence capability immediately.** Deferred; removing mutation
  authority is smaller, auditable, and sufficient for current workflows.
