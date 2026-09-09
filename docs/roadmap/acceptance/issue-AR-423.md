---
title: "AR-423 acceptance verification record"
status: active
category: roadmap
created: 2026-09-09
updated: 2026-09-09
tags: [acceptance, native, reliability]
related:
  - docs/roadmap/issue-AR-423-preserve-claude-hook-specialist-context.md
  - docs/worklog/2026-09-09-planner-repair-context.md
supersedes: []
superseded_by: null
type: acceptance-verification
issue_id: AR-423
candidate_commit: 320710dc2302f9764a69c3a9201a1feb964be3b3
evidence_cutoff: 2026-09-09
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/811
---

# AR-423 acceptance verification record

## Builder evidence

The builder cites evidence and does not judge criteria. Failed native turns remain
failed; this packet does not establish AR-404 all-host reliability.

| Criterion | Kind | Artifact | Observed | Source |
|---|---|---|---|---|
| 1 | file | Original 15.7KB native pointer substitution and native limit10,000UTF16, exact same-session trace | 2026-09-09 | docs/roadmap/evidence/AR-423-claude-native-hook-limit-20260909.json:1-14 |
| 1 | file | Original native follow-up pointer with accepted Store outcome preserved | 2026-09-09 | docs/roadmap/evidence/AR-404-claude-suite-after-repair-20260909.json:1-1150 |
| 2 | file | Fresh native session545f5ca7 has4exact selected-version card bodies in normal MCP results, five Store fields and accepted matching hash | 2026-09-09 | docs/roadmap/evidence/AR-404-claude-large-context-after-planner-context-20260909.json:1-540 |
| 2 | file | Exact two owner-approved per-tool Allow rules; no wildcard or other settings change | 2026-09-09 | docs/roadmap/evidence/AR-423-approved-tool-grant-20260909.json:1-15 |
| 2 | file | Turn and selected-version retrieval authorization with truthful pending/loaded split | 2026-09-09 | agency_runtime/core/claude_context_delivery.py:1-59 |
| 2 | file | Full-card retrieval stays bound to exact active trace and immutable selected version | 2026-09-09 | tests/test_claude_context_delivery.py:1-173 |
| 3 | command-output | Fresh12context regressions; focused143, production1151/3skipped, UI224, exact install615files and current native239.508s | 2026-09-09 | docs/worklog/2026-09-09-planner-repair-context.md:1-94 |
| 3 | command-output | Frozen candidate source188/188 conformance, no invalid or survived mutations | 2026-09-09 | docs/roadmap/evidence/AR-425-conformance-20260909.json:1-2626 |
| 3 | file | Verified wheel/source identity and normal five-host refresh | 2026-09-09 | docs/roadmap/evidence/AR-425-installed-candidate-20260909.json:1-916 |

| 1 | file | Exact original native hook attachment pointer, persisted byte/UTF16 counts and same-session trace correlation | 2026-09-09 | docs/roadmap/evidence/AR-423-original-native-pointer-20260909.json:1-50 |

## Verification

| Criterion | Verdict | Verifier run | Evidence digest | Observed | Reason |
|---|---|---|---|---|---|
