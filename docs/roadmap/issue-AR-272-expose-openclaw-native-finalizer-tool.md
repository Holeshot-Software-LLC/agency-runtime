---
title: "Expose OpenClaw native finalizer tool"
status: in_progress
category: roadmap
created: 2026-08-21
updated: 2026-08-21
tags: [openclaw, finalization, plugin, tool]
related:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/handoffs/issue-AR-119.md
  - docs/roadmap/issue-AR-271-preserve-openclaw-model-receipt-fields.md
  - docs/decisions/0120-construct-first-pass-evidence-headers.md
  - agency_runtime/core/installer_payload_manifests.py
  - agency_runtime/core/installer_payload_openclaw.py
  - agency_runtime/adapters/openclaw/node_bridge.py
  - tests/test_security_turn_boundaries.py
supersedes: []
superseded_by: null
type: issue
epic: reliability
issue_id: AR-272
priority: p0
tracker_url: null
depends_on: []
blocks: [AR-119]
---

# AR-272: Expose OpenClaw native finalizer tool

## Problem

The generated OpenClaw plugin instructed every Agency-enabled first pass to call
`agency.finalize`, but the native OpenClaw package exposed no such tool. Its
`.mcp.json` was retained in the installed bundle, while OpenClaw loaded the
package in native `openclaw` format and reported zero MCP servers and zero
tools. A model could not construct the Store-backed first visible response, so
strict finalization suppressed the invalid draft and the channel received no
reply.

## Current state

Fresh session `264a65e9-7462-4ea7-9b40-9b38206f1b35`, trace
`94f32f04-3b72-4ffa-8801-953b320e657f`, preserved four repaired
`task-general` model receipts but never called an Agency finalizer. Run
`2bf6cbd5-d7c9-417a-b423-eeb52b4646de` ended `response_invalid`;
finalization `a5b24d7f-933c-4aa3-8171-3d6ad0547cac` records all five
required fields missing. OpenClaw plugin inspection reports `toolNames: []`,
`tools: []`, and `mcpServers: []` even though the managed bundle contains
`.mcp.json`. This is failed evidence and grants no activation or delivery claim.

The executable generated-plugin regression failed before repair with Node exit
91 because `agency_finalize` was not registered. The bounded repair and 65
focused OpenClaw security, adapter, and installer tests pass; the first
unchanged companion invocation stopped before product assertions on the
repository temporary-namespace trust guard and is retained separately.

## Approach

Declare the provider-safe OpenClaw-native `agency_finalize` tool in the plugin
manifest and register it through OpenClaw's supported tool API. Dispatch its
bounded arguments to the existing canonical Agency `agency.finalize` Store
operation, return only the committed text, and teach OpenClaw preflight the
host-native identifier. Preserve first-pass-only finalization and the terminal
outbound gate; do not request a correction or allow an invalid draft.

## Dependencies

- OpenClaw `2026.7.1-2` native plugin tool and `contracts.tools` APIs.
- Existing Store-backed `agency.finalize` and exact outbound binding.
- AR-271 model-receipt preservation.

## Acceptance

- [x] A generated-plugin regression reproduces the absent native tool and fails pre-fix with Node exit 91.
- [x] The manifest declares `agency_finalize` and the native tool dispatches bounded arguments to canonical Store finalization.
- [x] Focused OpenClaw security-boundary, adapter, and installer tests pass 65/65; changed-file Ruff and formatting checks pass.
- [ ] A fresh install reports the native tool, and a new exact-status turn calls it once, completes first-pass finalization, and delivers the Store-backed response.
- [ ] Documentation and local verification gates pass.
- [ ] Tracker creation remains pending separate authorization.
