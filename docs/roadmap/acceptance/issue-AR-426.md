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
candidate_commit: a6d8f8a20ff92b27ce4919e179f1913a42110a58
evidence_cutoff: 2026-09-09
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/823
---

# AR-426 acceptance verification record

## Builder evidence

The builder cites evidence and does not judge criteria. Native acceptance for
criterion 3 is absent: both fixed phases and the single post-timeout attempt
failed full gates. Required fast checks passed, but cannot replace native proof.
No failed receipt is reopened. AR-426 remains blocked and its PR unmerged.

| Criterion | Kind | Artifact | Observed | Source |
|---|---|---|---|---|
| 1 | file | Exact native spill pointers and head/tail output, session/message IDs, source hashes and missing-context comparison | 2026-09-09 | docs/roadmap/evidence/AR-426-exact-native-hook-pointers-20260909.json:1-71 |
| 2 | file | Exact selected immutable version and whole-result size guard before recording a load | 2026-09-09 | agency_runtime/server/mcp_tools.py:207-294 |
| 2 | file | Active Hermes session/trace guard and ordered exact selected-card fragments | 2026-09-09 | agency_runtime/adapters/hermes/bridge.py:633-685 |
| 2 | test | Generated native tool regression and missing, cross-session, terminal, unselected, oversized and version-change cases | 2026-09-09 | tests/test_hermes_context_delivery.py:1-85 |
| 2 | test | Ordered callback regression checks full bodies, per-result native ceilings, current snapshot and cross-turn rejection | 2026-09-09 | tests/test_hermes_context_delivery.py:88-151 |
| 2 | command-output | Focused execution, required fast checks and immutable installed artifact identity; source checks only | 2026-09-09 | docs/roadmap/evidence/AR-426-compact-validation-20260909.json:1-35 |
| 3 | absent | none | 2026-09-09 | none |

## Verification

Second and final default pass for AR-426 after preserving exact native pointers.
The first record is retained in AR-426-isolated-pass1-record-20260909.txt.

| Criterion | Verdict | Verifier run | Evidence digest | Observed | Reason |
|---|---|---|---|---|---|
