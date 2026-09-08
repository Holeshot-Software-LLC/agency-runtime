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
| 1 | satisfied | `AR-420.1-20260908-ac570ab4` | `410fde7f43c39e24f821a90743fba776612f6ccb0fecc4f4e711525b2eff71ef` | 2026-09-08 | Evidence JSON 1-229 shows the real provider's original out-of-membership response failing as provider_response_contract_invalid plus a valid exact replay; inference.py:2343-2374 and 2735 send per-unit unit_id/candidate enums with minItems==maxItems, asserted by tests 1300-1353. |
| 2 | satisfied | `AR-420.2-20260908-066b15e0` | `52a520955865ba0d59b48dfbde11fede19b5112c85bb6a6bc222f9545babbb3a` | 2026-09-08 | inference.py:2343-2408 (used at 2735/2739) accepts any permutation yet rejects missing, duplicate, invented, cross-unit IDs and malformed units; test_recall_ranking_membership.py covers these, test_workforce_inference.py:1413-1459 shows typed-only recruiter fallback, AR-289 transport tests intact. |
| 3 | satisfied | `AR-420.3-20260908-376408aa` | `29dae8bdbead61a18eb09b1afcc34e68d41e41adc00c7ea2241a2365bf2cdfe5` | 2026-09-08 | Both cited evidence JSONs exist in the snapshot and match the issue and worklog exactly (replay 15.28s vs 25.561s capture, trace 01a0831f-1a40, 41.514s/28.148s, hash 275f342c matching finalization 9a0df117, source 3fe3d7ba, issue 802/PR 803); inference.py per-unit enum schema agrees. |
