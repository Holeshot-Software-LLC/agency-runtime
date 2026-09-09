---
title: "AR-427 acceptance verification record"
status: active
category: roadmap
created: 2026-09-09
updated: 2026-09-09
tags: [acceptance, reliability, delivery]
related:
  - docs/roadmap/issue-AR-427-preserve-complete-inferred-specialist-team.md
  - docs/worklog/2026-09-09-hermes-context-spill.md
supersedes: []
superseded_by: null
type: acceptance-verification
issue_id: AR-427
candidate_commit: 1c0e3c16921b38974b02280cf8334834a90ec0a3
evidence_cutoff: 2026-09-09
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/825
---

# AR-427 acceptance verification record

## Builder evidence

The builder cites evidence and does not judge. This is the first isolated pass.
The complete-team rule is shared across all five hosts; the fresh installed native
proof is one Hermes turn. Claude's fresh staffing failure and Codex's pending trust
review remain outside that passing native scope. Full source and evidence files
are present in the candidate snapshot when excerpts end.

| Criterion | Kind | Artifact | Observed | Source |
|---|---|---|---|---|
| 1 | file | Exact prior native selected team and missing fifth independent reviewer with session/trace | 2026-09-09 | docs/roadmap/evidence/AR-427-original-selected-team-omission-20260909.json:1-120 |
| 1 | file | Retained binding tail, delivered identities and omitted fifth assurance worker | 2026-09-09 | docs/roadmap/evidence/AR-427-original-selected-team-omission-20260909.json:121-156 |
| 2 | file | Complete-team hydration enforces selected-set equality before any load | 2026-09-09 | agency_runtime/core/specialist_context.py:344-397 |
| 2 | file | Shared preflight invokes complete-team delivery with existing context budget | 2026-09-09 | agency_runtime/core/preflight.py:1180-1230 |
| 2 | test | Five-host, native retrieval and missing/oversize regressions; final eight lines remain in snapshot | 2026-09-09 | tests/test_complete_selected_team.py:1-120 |
| 2 | test | Final no-load assertion for incomplete-team failures | 2026-09-09 | tests/test_complete_selected_team.py:121-128 |
| 2 | command-output | Corrected baseline and candidate test logs | 2026-09-09 | docs/roadmap/evidence/AR-427-causal-baseline-summary-20260909.json:1-26 |
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
| 1 | satisfied | `AR-427.1-20260909-d32ea9de` | `66f90abc5d55358f481c988e27607c4fe1f372614fd711568c7157ed1fde23d1` | 2026-09-09 | Snapshot file AR-427-original-selected-team-omission-20260909.json matches the excerpts exactly and records session_id, trace_id, five routing_selected_ids vs four observed_loaded, omitted_selected_ids ai-generated-code-security-auditor, plus per-unit role bindings and specialist refs. |
| 2 | satisfied | `AR-427.2-20260909-7cd12f81` | `67b8a4e33b0ee52cbbd8aec9f141c2cff80e6dfdeb23a693a71abcbbf1afc8e7` | 2026-09-09 | specialist_context.py:377-391 raises RuntimeError when delivered slugs differ from selected_ids, before any load is recorded; preflight.py:1211-1221 passes require_complete with a context-derived budget; _fit_loaded_context keeps the char and 16-ref ceilings; tests cover 5 hosts and 3 fault modes. |
| 3 | satisfied | `AR-427.3-20260909-653edb20` | `1788cca8b3774b970a8f82ef7708c4b883270f697209fd6362b5b1d86a58fb45` | 2026-09-09 | AR-427-compact-validation shows focused 66 passed/1 skipped, production 1151/3, UI 224, ruff clean, 188/188 conformance, wheel with 616 installed files and zero mismatches; the Hermes run at installed_source 20c49e0d kept all five cards with all_five_match true and an authoritative accept. |
