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
| 1 | absent | `AR-423.1-20260909-aff6ed5e` | `261ddfcb87b821de9368c1593fb7a276654bf626d52f8e9351a83f126eead6b5` | 2026-09-09 | The native-limit excerpt establishes the 10,000-unit limiter, but the AR-404 excerpt contains no pointer substitution or same-session follow-up trace demonstrating reproduction. |
| 2 | absent | `AR-423.2-20260909-779c4d4e` | `755e0cae94775ec8a6c1ce80c4b152119bd2b1993f25b3ef331d3ac491589bd0` | 2026-09-09 | The native probe excerpt shows routing and finalization but no full-card MCP results; claude_context_delivery.py and the test excerpt do not demonstrate caller-scope, trust, and independent-assurance enforcement. |
| 3 | satisfied | `AR-423.3-20260909-4833b3df` | `6aa88370036f53755a623570be79e36d590b86be99fb8a7937216f9f981349f1` | 2026-09-09 | The worklog records 12 Claude context regressions passing and a fresh native session completing in 239.508 seconds with four exact full cards and all five Store fields matching; the installation artifact reports 615 files with no mismatches. |
