---
title: "Expose Hermes native finalizer tool"
status: done
category: roadmap
created: 2026-08-25
updated: 2026-08-27
tags: [hermes, finalization, plugin, tool, reliability]
related:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-264-compile-actionable-contractor-execution-profiles.md
  - docs/roadmap/issue-AR-266-dense-hybrid-workforce-recall.md
  - docs/roadmap/issue-AR-273-expose-openclaw-native-finalizer-tool.md
  - docs/roadmap/issue-AR-287-bind-host-hook-timeouts-to-inference-budgets.md
  - docs/roadmap/issue-AR-297-complete-unattended-container-bootstrap.md
  - docs/roadmap/handoffs/issue-AR-266.md
  - docs/roadmap/handoffs/issue-AR-297.md
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
- Agency alone was reinstalled from this checkout. Hermes's native config
  remained byte-identical at SHA-256
  `95b87b7fc0427ad4e3da4f5f468054cf9f7ddba679d1bb606b782a13e1a0172d`,
  the native inventory reported the `agency-runtime` toolset, and launcher
  manifest SHA-256 became
  `cd025c3589d9ca8f592ae1e24114fee9df2b8477420f80ac518ea9b993c59f93`.
- Fresh Hermes session `20260825_112803_2eae8e`, trace
  `20260825_112803_2eae8e:fbbb0bcf-ef22-40de-bbd4-030fb5919eb9:cb12755e`,
  completed through native `agency_finalize`. Terminal finalization
  `e87cec42-c0db-4252-8e92-5c64c556980f` committed response SHA-256
  `91c4a26d30097a6bf18e55dfb792d7c6e1532fe6ba61bca723596b847470daa4`.
  The same Store-backed turn applied the exact LiteLLM alias
  `task-agency-router`, local `qwen3-embedding:latest`, and local
  `qwen3-14b-abliterated:latest`; Hermes's native answer receipt remained
  `task-general`. The LiteLLM alias is not promoted to an underlying-model
  claim because proxy callback telemetry did not supply one.
- Two changed probes are retained as useful fail-closed evidence: one applied
  both local recall stages but exceeded the inline finalizer transport bound;
  another applied both stages but exhausted recruiter repair on
  `staff_without_safe_team`. Neither was retried unchanged.
- Tracker creation is pending explicit authorization.
- AR-297's exact Hermes `0.20.4` production-container R5 exposed two current
  compatibility gaps hidden by the earlier live pass. Default progressive tool
  disclosure deferred `agency_finalize`, and after an exact native config
  diagnostic made it eager, Qwen called the finalizer once but paraphrased its
  2,625-byte result on Hermes's mandatory follow-up model turn. Store committed
  the accepted exact hash, then the existing output hook correctly withheld the
  rewritten text. The visible process therefore remained fail-closed rather
  than satisfying this issue's exact-emission acceptance.
- Red-before regression `cad6beee...d937` exits 1 on that exact boundary. The
  bounded repair teaches default tool-search discovery and keeps the native
  finalizer result in a 1,024-entry, trace-scoped, one-shot in-memory cache.
  The transform hook returns it only when a separate bridge call proves the
  same text hash is already the authoritative completed acceptance. Rejected,
  mismatched, repeated, disabled-runtime, or unavailable-Agency paths preserve
  their prior behavior. Four focused suites pass 236 tests at
  `68ade380...3ffc`.
- Clean candidate `e17e5221657ec90df8092879cf9d5c79d65ecb50` rebuilds and
  independently verifies exact artifacts/images. Fresh UID-10000 Hermes R2
  absence, exact default native config, dry-run, sole install, status, and
  plugin-doctor receipts all exit 0; the installed bundle registers one native
  finalizer and eight hooks. Fresh ordinary session
  `20260827_201909_a6a13c` then exits 0 with one exact 3,227-byte specialist
  card, one `agency_finalize`, authoritative accepted response
  `ad8a06d3...eeaa`, and byte-identical visible output. Independent receipt
  `3c40a9bf...8959` also proves Store/native quick-checks, `missing=[]`, the
  mandatory model follow-up differs, and the post-install/default native config
  remains byte-identical across the live turn at `2552f21c...e680`.

## Approach

Register one generated-plugin tool through Hermes's supported native API using
a host-valid identifier such as `agency_finalize`. Forward only bounded draft
text plus the plugin's active session/trace correlation through the existing
subprocess bridge. Dispatch the canonical Store finalizer with the authoritative
originating Hermes run, and return its committed text for byte-exact emission.
Teach preflight the actual host-native identifier and its 3,000-character draft
budget. Construct before commit, reject output above the inline-safe ceiling,
then revalidate and atomically commit the exact result.

Preserve first-pass finalization and terminal rejection. Under Hermes's default
progressive disclosure, explicitly discover the exact finalizer without a
schema-description round trip. Cache only the bounded result returned by that
correlated native call, then replay it over any follow-up model rewrite only
after the bridge independently matches its authoritative completed Store hash.
Do not repair a response without that acceptance, request a second model pass,
accept stale evidence, or modify native Hermes configuration/source.

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
- [x] Agency alone is reinstalled into Hermes without changing native config,
      and the native inventory reports the tool.
- [x] One genuinely new Hermes turn calls the tool once, emits its exact accepted
      text, and records successful finalization plus parent/embedding/reranker
      receipts.
- [x] Focused tests and proportionate repository gates pass.
- [x] Tracker creation remains pending separate authorization.
- [x] A red-before regression covers a model rewriting an already accepted
      native finalizer result; replay is bounded, one-shot, and trace-scoped.
- [x] Default Hermes tool-search guidance discovers `agency_finalize` without
      requiring native config drift.
- [x] Rebuilt exact artifacts pass a fresh default-config Hermes turn whose
      visible output is the byte-exact accepted tool result.
