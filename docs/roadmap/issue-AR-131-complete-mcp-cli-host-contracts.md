---
title: "AR-131: Complete MCP and CLI host contracts"
status: open
category: roadmap
created: 2026-07-26
updated: 2026-07-26
tags: [mcp, cli, host-integrations, schema, compatibility]
related:
  - agency_runtime/server/mcp.py
  - agency_runtime/server/mcp_tools.py
  - agency_runtime/core/host_control.py
  - tests/test_mcp_protocol_hardening.py
supersedes: []
superseded_by: null
type: issue
epic: host-integrations
issue_id: AR-131
priority: p0
tracker_url: null
depends_on: []
blocks: []
---

# AR-131: Complete MCP and CLI host contracts

## Problem

Valid host-bearing MCP calls fail the server's own fail-closed string-schema
validator because their `host` fields omit `maxLength`. Independently copied
host enums omit ZCode and can drift from the canonical supported-host set.
Delegation schema maxima also exceed the Store's canonical identifier bounds.

## Current state

Protocol dispatch of valid `agency.preflight` and `agency.host_status` requests
with `host="codex"` returns an error before the handler. Direct-handler tests
hide the defect. Model-callable host mutation is also incompatible with the
authority decision in AR-128.

## Approach

Generate read-only host and delegation tool schemas from shared constants, add
explicit bounds to every string property, remove model-callable mutations, and
add protocol-level success tests plus a schema-wide invariant test. Reconcile
CLI, HTTP, MCP, and generated skill documentation from one tool registry.

## Dependencies

AR-128 owns mutation authority. AR-135 owns ZCode installation behavior.

## Acceptance

- Every published MCP string property has an explicit valid maximum length.
- Valid preflight and status requests dispatch through the real protocol.
- All read-only host schemas derive from the canonical five-host set.
- Accepted delegation identifiers persist exactly without truncation.
- Generated tool and skill surfaces match the runtime registry exactly.
- Invalid, unknown, oversized, and mutation requests fail closed.
