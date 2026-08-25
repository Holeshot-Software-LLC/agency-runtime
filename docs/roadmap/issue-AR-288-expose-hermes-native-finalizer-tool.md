---
title: "Expose Hermes native finalizer tool"
status: in_progress
category: roadmap
created: 2026-08-25
updated: 2026-08-25
tags: [hermes, finalization, plugin, tool, reliability]
related:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-264-compile-actionable-contractor-execution-profiles.md
  - docs/roadmap/issue-AR-266-dense-hybrid-workforce-recall.md
  - docs/roadmap/issue-AR-273-expose-openclaw-native-finalizer-tool.md
  - docs/roadmap/issue-AR-287-bind-host-hook-timeouts-to-inference-budgets.md
  - docs/roadmap/handoffs/issue-AR-266.md
  - docs/decisions/0120-construct-first-pass-evidence-headers.md
  - agency_runtime/core/installer_payload_hermes.py
  - agency_runtime/adapters/hermes/bridge.py
  - tests/test_completion_policy_boundary.py
supersedes: []
superseded_by: null
type: issue
epic: reliability
issue_id: AR-288
priority: p0
tracker_url: null
depends_on: []
blocks: []
---

# AR-288: Expose Hermes native finalizer tool

## Problem

The generated Hermes plugin tells each Agency-enabled turn to call
`agency.finalize` immediately before its first visible response, but it
registers no model-callable finalizer tool. The effective Hermes configuration
also has no Agency MCP server. A model therefore cannot deterministically
construct the current Store-backed header after tool and host-model evidence
changes; an honest stale header is correctly blocked by strict finalization.

## Current state

- Hermes Agent `0.20.4` supports plugin-native tools through
  `PluginContext.register_tool`, but the installed Agency plugin registers only
  eight hooks and the read-only `/agency` command.
- The native CLI tool inventory contains no Agency finalizer, and the effective
  Hermes MCP inventory contains no Agency server.
- Fresh trace
  `20260825_100145_81c6d2:1ebe5369-b94a-4df6-8cc8-7ec6875e66f9:5dc384f7`
  proves AR-287's repaired timeout and all three provider stages. Its artificial
  eight-iteration cap then forced a no-tool summary whose stale header was
  correctly rejected. That max-turn failure is not itself an AR-288 regression;
  inspection of the installed tool surface is the missing-tool evidence.
- OpenClaw's equivalent defect and native-tool pattern are preserved in AR-273.
  No Hermes native config or source change is required.
- The repository repair now registers the bounded native tool, derives
  correlation only from Hermes callback state, dispatches canonical
  finalization, and preserves accepted text byte-for-byte. It commits only
  responses at or below the 4,096-character inline ceiling, safely below
  Hermes `0.20.4`'s 8,000-character spill floor; enabled oversized drafts stay
  active while disabled runtime remains exact passthrough. The focused
  generated-plugin, completion-boundary, adapter, and bridge-encoding checks
  pass (109 tests),
  including a red-before exact-text boundary regression.
- Tracker creation is pending explicit authorization.

## Approach

Register one generated-plugin tool through Hermes's supported native API using
a host-valid identifier such as `agency_finalize`. Forward only bounded draft
text plus the plugin's active session/trace correlation through the existing
subprocess bridge. Dispatch the canonical Store finalizer with the authoritative
originating Hermes run, and return its committed text for byte-exact emission.
Teach preflight the actual host-native identifier and its 3,000-character draft
budget. Construct before commit, reject output above the inline-safe ceiling,
then revalidate and atomically commit the exact result.

Preserve first-pass finalization and terminal rejection. Do not repair a natural
response after rejection, request a second model pass, accept stale evidence,
or modify native Hermes configuration/source.

## Dependencies

- Hermes Agent `0.20.4` native plugin tool registration and handler contracts.
- Existing bounded bridge projection and current-turn correlation.
- Existing canonical `agency.finalize` Store transaction and accepted-response
  replay behavior.
- AR-287's shared 595-second bridge/lease budget.

## Acceptance

- [x] A generated-plugin regression fails before repair because no Hermes
      native finalizer tool is registered.
- [x] The plugin registers one bounded `agency_finalize` tool and preflight
      instructs the model to call that exact identifier once.
- [x] The bridge invokes canonical finalization with the current Hermes
      session/trace and never trusts model-supplied correlation or host identity.
- [x] Malformed, missing, stale, raced, or rejected evidence remains fail-closed
      under the existing terminal policy.
- [ ] Agency alone is reinstalled into Hermes without changing native config,
      and the native inventory reports the tool.
- [ ] One genuinely new Hermes turn calls the tool once, emits its exact accepted
      text, and records successful finalization plus parent/embedding/reranker
      receipts.
- [x] Focused tests and proportionate repository gates pass.
- [x] Tracker creation remains pending separate authorization.
