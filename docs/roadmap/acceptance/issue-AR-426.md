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
candidate_commit: pending
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
