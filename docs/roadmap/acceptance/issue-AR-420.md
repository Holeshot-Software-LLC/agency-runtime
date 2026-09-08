---
title: "AR-420 acceptance verification record"
status: active
category: roadmap
created: 2026-09-08
updated: 2026-09-08
tags: [acceptance, reranker, verification]
related:
  - docs/roadmap/issue-AR-420-bind-reranker-candidate-membership.md
  - docs/worklog/2026-09-08-reranker-membership-repair.md
supersedes: []
superseded_by: null
type: acceptance-verification
issue_id: AR-420
candidate_commit: 86c99a36ec5fc2420f46cb57e70deda58e480e35
evidence_cutoff: 2026-09-08
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/802
---

# AR-420 acceptance verification record

## Builder evidence

This record cites observations; independent verification supplies verdicts.

| Criterion | Kind | Artifact | Observed | Source |
|---|---|---|---|---|
| 1 | file | Captured offered sets, rejected response and exact-request replay | 2026-09-08 | docs/roadmap/evidence/AR-420-reranker-membership-20260908.json:1-229 |
| 1 | test | Structured transport receives per-unit identity, membership and counts | 2026-09-08 | tests/test_workforce_inference.py:1300-1353 |
| 1 | command-output | Original-source regression and candidate results | 2026-09-08 | docs/worklog/2026-09-08-reranker-membership-repair.md#challenges-encountered |
| 2 | test | All permutations and negative membership/unit cases | 2026-09-08 | tests/test_recall_ranking_membership.py:1-51 |
| 2 | test | Invalid optional reranking preserves typed-only fallback | 2026-09-08 | tests/test_workforce_inference.py:1414-1465 |
| 2 | test | Native reranker transport and rejection tests | 2026-09-08 | tests/test_workforce_reranker_provider.py:1-279 |
| 2 | file | Bounded schema production change and unchanged parser | 2026-09-08 | agency_runtime/core/workforce/inference.py:2343-2440 |
| 2 | command-output | Focused, production and frozen-source conformance outcomes | 2026-09-08 | docs/worklog/2026-09-08-reranker-membership-repair.md#verification |
| 3 | file | Real-provider capture and changed-schema replay | 2026-09-08 | docs/roadmap/evidence/AR-420-reranker-membership-20260908.json:1-229 |
| 3 | file | Fresh installed native turn, all stages applied, exact card and final response | 2026-09-08 | docs/roadmap/evidence/AR-420-native-codex-20260908.json:1-169 |
| 3 | command-output | Installed wheel identity, exact byte check and validation | 2026-09-08 | docs/worklog/2026-09-08-reranker-membership-repair.md#verification |
| 3 | file | Canonical scope, limitations and tracker mapping | 2026-09-08 | docs/roadmap/issue-AR-420-bind-reranker-candidate-membership.md:1-78 |

## Verification

| Criterion | Verdict | Verifier run | Evidence digest | Observed | Reason |
|---|---|---|---|---|---|
