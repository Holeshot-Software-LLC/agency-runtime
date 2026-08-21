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

After installing that Agency integration, fresh OpenClaw session
`5793b45e-0a29-4a37-849c-1451aae6880c` and trace
`f3ca497b-ec59-4dfe-b9c6-845e8605f5b5` completed exact control text
`agency status`. Run `abc5ea35-9b0d-4c39-8750-b10f0521e4a5` is
`completed`; finalization `b77b9deb-4630-47a4-bf68-9e248d368e9c` accepted
once, and its response hash exactly matches the 622-byte assistant text in
native transcript SHA-256
`8aa5be1a91131213de7980d6d53d1a2d206fa06d97b6a3bd7fdc75eacdee269a`.
The ready recipe carries request-scoped binding
`rmb-c1598ad69b8b0033b69e9b89ae4c063f`; by design OpenClaw does not retain
a persistent `resident_manager_bindings` row.

That live receipt exposed a second defect: the native wrapper reused the public
MCP dispatcher, so the accepted event was incorrectly labeled `host=mcp` even
though the authoritative run host is `openclaw`. A focused regression preserves
`mcp != openclaw` as the red assertion. The OpenClaw-only bridge repair calls
the same canonical finalizer with native host identity; the MCP surface and all
other harnesses remain unchanged. The focused regression and the complete
65-test OpenClaw slice pass under an owner-private `0022` test namespace.

## Approach

Declare the provider-safe OpenClaw-native `agency_finalize` tool in the plugin
manifest and register it through the supported OpenClaw native tool API. Dispatch its
bounded arguments to the canonical Store finalizer with `host=openclaw`, return
only the committed text, and teach OpenClaw preflight the host-native
identifier. Keep the public MCP dispatcher labeled `mcp`. Preserve
first-pass-only finalization and the terminal outbound gate; do not request a
correction or allow an invalid draft.

## Dependencies

- OpenClaw `2026.7.1-2` native plugin tool and `contracts.tools` APIs.
- Existing Store-backed `agency.finalize` and exact outbound binding.
- AR-271 model-receipt preservation.

## Acceptance

- [x] A generated-plugin regression reproduces the absent native tool and fails pre-fix with Node exit 91.
- [x] The manifest declares `agency_finalize` and the native tool dispatches bounded arguments to canonical Store finalization.
- [x] A fresh Agency integration install reports the native tool; a new exact-status turn calls it once, completes first-pass finalization, and delivers the hash-bound Store response.
- [x] A focused Store assertion preserves the live native-host mismatch as red (`mcp != openclaw`).
- [x] The OpenClaw wrapper supplies `host=openclaw`; focused OpenClaw security-boundary, adapter, and installer tests pass 65/65.
- [ ] Reinstall the repaired Agency integration and require a genuinely new exact-status receipt whose accepted finalization is labeled `openclaw`.
- [ ] Documentation and local verification gates pass.
- [ ] Tracker creation remains pending separate authorization.
