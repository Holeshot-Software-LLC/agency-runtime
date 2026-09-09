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
candidate_commit: 38fa9e437fa0070fe85eac05c456e0ef093ef17c
evidence_cutoff: 2026-09-09
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/811
---

# AR-423 acceptance verification record

## Builder evidence

The builder cites evidence and does not judge criteria. Failed native turns remain
failed; this packet does not establish AR-404 all-host reliability.

| Criterion | Kind | Artifact | Observed | Source |
|---|---|---|---|---|
| 1 | file | Exact native attachment pointer, timestamp, persisted size, hash and session/trace correlation | 2026-09-09 | docs/roadmap/evidence/AR-423-original-native-pointer-20260909.json:1-27 |
| 1 | file | Read-only native binary limit and exact baseline scope | 2026-09-09 | docs/roadmap/evidence/AR-423-claude-native-hook-limit-20260909.json:1-14 |
| 2 | file | Exact native tool use/result, immutable selected reference, full card and separate appended disclosure | 2026-09-09 | docs/roadmap/evidence/AR-423-native-full-card-application-security-engineer-20260909.json:1-39 |
| 2 | file | Exact native tool use/result, immutable selected reference, full card and separate appended disclosure | 2026-09-09 | docs/roadmap/evidence/AR-423-native-full-card-backend-service-engineer-20260909.json:1-40 |
| 2 | file | Exact native tool use/result, immutable selected reference, full card and separate appended disclosure | 2026-09-09 | docs/roadmap/evidence/AR-423-native-full-card-code-reviewer-20260909.json:1-39 |
| 2 | file | Exact native tool use/result, immutable selected reference, full card and separate appended disclosure | 2026-09-09 | docs/roadmap/evidence/AR-423-native-full-card-technical-writer-20260909.json:1-39 |
| 2 | file | Two exact approved native per-tool rules | 2026-09-09 | docs/roadmap/evidence/AR-423-approved-tool-grant-20260909.json:1-15 |
| 2 | file | Selected version and active-turn guards before load recording | 2026-09-09 | agency_runtime/server/mcp_tools.py:207-290 |
| 2 | file | Accepted native terminal, exact Store headers and retained response hash | 2026-09-09 | docs/roadmap/evidence/AR-423-native-terminal-summary-20260909.json:1-86 |
| 3 | command-output | Recorded focused, fast and native validation with exact scope and limitations | 2026-09-09 | docs/worklog/2026-09-09-planner-repair-context.md:28-94 |
| 3 | file | Canonical installed artifact and frozen conformance summary | 2026-09-09 | docs/roadmap/evidence/AR-423-compact-installed-validation-20260909.json:1-22 |
| 3 | file | Fresh native invocation and authoritative terminal evidence with matching headers | 2026-09-09 | docs/roadmap/evidence/AR-423-native-terminal-summary-20260909.json:1-86 |

## Verification

Owner authorized one additional isolated pass on 2026-09-09 ("go for it").
Earlier failed passes remain preserved; this is the third pass, not a retry loop.

| Criterion | Verdict | Verifier run | Evidence digest | Observed | Reason |
|---|---|---|---|---|---|
| 1 | satisfied | `AR-423.1-20260909-481b2034` | `0f3a6aa2b2703c07429e442b681d74eed136c134e77a67f441ced19bae56a0e1` | 2026-09-09 | AR-423-original-native-pointer-20260909.json captures the exact substitution, timestamp, size, hashes and session/trace correlation; AR-423-claude-native-hook-limit-20260909.json shows the native 10,000-unit limiter exceeded by the 16,067-unit output. |
| 2 | absent | `AR-423.2-20260909-1cdde5fb` | `a876e3ce2df7354000345044c6f6362e0e08be2b171a6e42948353646c372d26` | 2026-09-09 | The full-card receipts and mcp_tools.py demonstrate native delivery and turn guards, but the terminal summary records no delegation and does not establish preservation of independent assurance. |
| 3 | satisfied | `AR-423.3-20260909-c12f936f` | `3166cbf7b5a6b26bc784a8778e119b20689ea6961cf17883f3eb588944baa88e` | 2026-09-09 | The worklog records passing regression suites, the installed validation artifact reports 188/188 conformance mutations killed, and the native terminal summary records a fresh session with accepted authoritative completion and matching headers. |
