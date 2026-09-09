---
title: "AR-424 acceptance verification record"
status: active
category: roadmap
created: 2026-09-09
updated: 2026-09-09
tags: [acceptance, native, exact-delivery]
related:
  - docs/roadmap/issue-AR-424-preserve-last-card-whitespace.md
  - docs/worklog/2026-09-09-claude-native-context-delivery.md
supersedes: []
superseded_by: null
type: acceptance-verification
issue_id: AR-424
candidate_commit: 7a26e48992085ac7b4a56f2c52aa25541dc0bb62
evidence_cutoff: 2026-09-09
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/812
---

# AR-424 acceptance verification record

## Builder evidence

These rows describe the shared bridge's exact-card byte scope. They do not judge
criteria or claim all-host reliability. AR-423 owns the separate large-Claude
native retrieval gate; its pending proof does not disappear from that issue.

| Criterion | Kind | Artifact | Observed | Source |
|---|---|---|---|---|
| 1 | file | Original recipe-15 real bridge fails the exact four-card assertion before the final trim is removed | 2026-09-09 | docs/roadmap/evidence/AR-423-context-delivery-validation-20260909.json:1-54 |
| 1 | file | Real Store and HookBridge fixture preserves exact leading/trailing body bytes in its assertion | 2026-09-09 | tests/test_claude_context_delivery.py:16-72 |
| 1 | file | Shared-host regression asserts all complete bodies in emitted native context | 2026-09-09 | tests/test_claude_context_delivery.py:139-142 |
| 2 | file | Shared bridge joins the original context without stripping card bytes | 2026-09-09 | agency_runtime/adapters/hooks.py:2580-2608 |
| 2 | file | Passing real-hook regression, exact selected versions, unchanged selection and terminal boundaries | 2026-09-09 | tests/test_claude_context_delivery.py:58-142 |
| 2 | file | Governed delivery surface and unchanged inference, critic and finalization policy | 2026-09-09 | docs/decisions/0241-deliver-large-claude-card-sets-through-versioned-mcp.md#decision |
| 3 | command-output | 166 focused passed/6 skipped, 1151 production passed/3 skipped, UI224 and source conformance188/188 | 2026-09-09 | docs/roadmap/evidence/AR-423-context-delivery-validation-20260909.json:1-54 |
| 3 | command-output | Ruff check and formatting, negative controls and retained failed intermediate run | 2026-09-09 | docs/worklog/2026-09-09-claude-native-context-delivery.md#verification |

| 3 | command-output | Fresh-source conformance has 188 killed, no survivors or invalid mutations and unchanged source | 2026-09-09 | docs/roadmap/evidence/AR-423-context-delivery-validation-20260909.json:130-143 |

| 3 | command-output | Exact matching production/test Git trees and fresh named real shared-host whitespace check | 2026-09-09 | docs/roadmap/evidence/AR-424-shared-host-validation-20260909.json:1-55 |
| 3 | file | Actual named shared-host whitespace regression in this candidate | 2026-09-09 | tests/test_claude_context_delivery.py:139-142 |

## Verification

| Criterion | Verdict | Verifier run | Evidence digest | Observed | Reason |
|---|---|---|---|---|---|
| 1 | satisfied | `AR-424.1-20260909-04121983` | `83974571bedeaeae9a4a225eef2d62341cef13ebf380393cd247be8eedb08044` | 2026-09-09 | AR-423-context-delivery-validation JSON logs.original_final_card shows test_other_hosts_keep_inline_delivery failing the byte-exact all(body in context) assert on pre-fix source; tests/test_claude_context_delivery.py:18-61,139-142 drives it via real Store/HookBridge with trailing-whitespace bodies. |
| 2 | satisfied | `AR-424.2-20260909-6dbff237` | `ec568ecad6a341224a2b22ab2ba63e298a590bfe4fcc8a4b6abc93be441767c9` | 2026-09-09 | Byte-exact preservation shown: roster.py:2288-2296 hash-checks stored content, mcp_tools.py:249 returns it unstripped, hooks.py:2587-2594 and _combine_context join without trimming, and tests lines 23/85-86/140 assert cards with leading and trailing whitespace survive; loads stay evidence-gated. |
| 3 | satisfied | `AR-424.3-20260909-5b3a847c` | `3c2efb31f6d6cdc083c17b9a479cea22e3bf33668763a8f195f5c1feb7cffb85` | 2026-09-09 | AR-424-shared-host-validation JSON logs the focused zcode regression passing with trees identical to production cd86e40a; AR-423 JSON and worklog show spine 1151/3, focused 166/6, UI 224, ruff and conformance 188/188; test and unstripped join present at candidate. |
