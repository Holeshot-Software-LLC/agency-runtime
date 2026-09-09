---
title: "AR-426 acceptance verification record"
status: active
category: roadmap
created: 2026-09-09
updated: 2026-09-09
tags: [acceptance, hermes, reliability]
related:
  - docs/roadmap/issue-AR-426-preserve-hermes-hook-specialist-context.md
  - docs/worklog/2026-09-09-hermes-context-spill.md
supersedes: []
superseded_by: null
type: acceptance-verification
issue_id: AR-426
candidate_commit: 1c0e3c16921b38974b02280cf8334834a90ec0a3
evidence_cutoff: 2026-09-09
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/823
---

# AR-426 acceptance verification record

## Builder evidence

The builder cites evidence and does not judge. This third pass is explicitly
owner-authorized on 2026-09-09. Both prior records remain retained. Exact original
missing-context files and complete new native cards are present in the candidate
snapshot; inspect those cited files when excerpts end. No failed receipt is reopened.

| Criterion | Kind | Artifact | Observed | Source |
|---|---|---|---|---|
| 1 | file | Original native pointer substitutions with exact head and tail | 2026-09-09 | docs/roadmap/evidence/AR-426-exact-native-hook-pointers-20260909.json:1-71 |
| 1 | file | Full saved missing context for native message 535347; remainder available in the candidate snapshot | 2026-09-09 | docs/roadmap/evidence/AR-426-original-missing-context-535347-20260909.txt:1-100 |
| 1 | file | Full saved missing context for native message 535352; remainder available in the candidate snapshot | 2026-09-09 | docs/roadmap/evidence/AR-426-original-missing-context-535352-20260909.txt:1-100 |
| 1 | file | Exact byte lengths and hashes for both saved files | 2026-09-09 | docs/roadmap/evidence/AR-426-preserved-missing-context-manifest-20260909.json:1-20 |
| 2 | file | Selected immutable version and whole-result bound before load recording | 2026-09-09 | agency_runtime/server/mcp_tools.py:207-294 |
| 2 | file | Hermes active session/trace guard and ordered full-card callback delivery | 2026-09-09 | agency_runtime/adapters/hermes/bridge.py:633-685 |
| 2 | test | Missing, cross-turn, unselected, oversized and version-change rejection | 2026-09-09 | tests/test_hermes_context_delivery.py:1-85 |
| 2 | test | Exact ordered callbacks, bounded results and truthful loads | 2026-09-09 | tests/test_hermes_context_delivery.py:88-151 |
| 2 | command-output | Focused checks and native installed identity | 2026-09-09 | docs/roadmap/evidence/AR-427-compact-validation-20260909.json:1-49 |
| 3 | file | Full native card text with exact selected immutable reference, native message and context offsets | 2026-09-09 | docs/roadmap/evidence/AR-427-hermes-full-card-application-security-engineer-20260909.json:1-22 |
| 3 | file | Full native card text with exact selected immutable reference, native message and context offsets | 2026-09-09 | docs/roadmap/evidence/AR-427-hermes-full-card-code-reviewer-20260909.json:1-22 |
| 3 | file | Full native card text with exact selected immutable reference, native message and context offsets | 2026-09-09 | docs/roadmap/evidence/AR-427-hermes-full-card-python-application-engineer-20260909.json:1-23 |
| 3 | file | Full native card text with exact selected immutable reference, native message and context offsets | 2026-09-09 | docs/roadmap/evidence/AR-427-hermes-full-card-silent-failure-hunter-20260909.json:1-23 |
| 3 | file | Full native card text with exact selected immutable reference, native message and context offsets | 2026-09-09 | docs/roadmap/evidence/AR-427-hermes-full-card-software-test-engineer-20260909.json:1-23 |
| 3 | file | Native session, complete inferred and retained team, exact five Store headers and authoritative finalization | 2026-09-09 | docs/roadmap/evidence/AR-427-hermes-terminal-summary-20260909.json:1-97 |
| 3 | command-output | Focused and required fast results, canonical installed artifact and 616 matching files | 2026-09-09 | docs/roadmap/evidence/AR-427-compact-validation-20260909.json:1-49 |

## Verification

| Criterion | Verdict | Verifier run | Evidence digest | Observed | Reason |
|---|---|---|---|---|---|
| 1 | satisfied | `AR-426.1-20260909-bb4cf179` | `0386eb7c540a309f072c912fb0a626d971db38451baee35bc31e60f73d97a6bc` | 2026-09-09 | Snapshot holds AR-426-exact-native-hook-pointers-20260909.json with the verbatim truncation banner and head/tail for messages 535347 and 535352, plus both AR-426-original-missing-context txt files whose first and last lines (237/317) match those fragments and the manifest char/line/sha256 records. |
| 2 | satisfied | `AR-426.2-20260909-73ca814f` | `c3a3d0d720172d0536163046c84858e5965016eecc5788741e455257d1e41eda` | 2026-09-09 | mcp_tools.py:279-292 applies the Hermes result bound before record_specialist_loaded; tests/test_hermes_context_delivery.py:16-152 assert exact card bodies, loads matching selection, and error-with-no-load for unselected, other-session, missing-trace, terminal, oversized and cross-turn cases. |
| 3 | satisfied | `AR-426.3-20260909-eaba9409` | `c4f45a10b15971eb35f8bdd496049f2599a06124ff1dc175d10cdfdab7354a13` | 2026-09-09 | AR-427-compact-validation shows focused 66, production 1151, UI 224, conformance 188/188 and recipe 19 installed 616-file match; five full-card files match the native context artifact; the terminal summary shows all_five_match true and authoritative accepted finalization matching the response file. |
