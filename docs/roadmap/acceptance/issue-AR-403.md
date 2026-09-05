---
title: "AR-403 acceptance verification record"
status: active
category: roadmap
created: 2026-09-05
updated: 2026-09-05
tags: [acceptance, verification, staffing]
related:
  - docs/roadmap/issue-AR-403-reuse-roster-embeddings-across-hook-processes.md
  - docs/roadmap/handoffs/issue-AR-400.md
supersedes: []
superseded_by: null
type: acceptance-verification
issue_id: AR-403
candidate_commit: 1de05aead322dbbf359a0a5f3ab19dcbb7cdeff9
evidence_cutoff: 2026-09-05
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/668
---

# AR-403 acceptance verification record

Candidate is the implementation merged through PR #669. Builder rows identify
observable artifacts; the isolated verifier alone supplies judgments.

## Builder evidence

| Criterion | Kind | Artifact | Observed | Source |
|---|---|---|---|---|
| 1 | test | `Two separate interpreters embed three then one inputs, retaining identical candidates and excluding query text from storage` | 2026-09-05 | `tests/test_persistent_hybrid_recall_cache.py:21-81` |
| 1 | file | `Exact float64 vectors, bounded decode and private file validation` | 2026-09-05 | `agency_runtime/core/workforce/catalog_vector_cache.py:24-111` |
| 2 | test | `Identity, roster, directory, expiry, corruption and actual-model mismatch invalidate cached vectors` | 2026-09-05 | `tests/test_persistent_hybrid_recall_cache.py:84-120` |
| 2 | test | `Symlinks, hard links and public cache paths become misses without modifying their targets` | 2026-09-05 | `tests/test_persistent_hybrid_recall_cache.py:156-181` |
| 2 | file | `Cache reads validate identity, freshness, shape and normalization; faults return a miss` | 2026-09-05 | `agency_runtime/core/workforce/catalog_vector_cache.py:113-203` |
| 3 | command-output | `Current cold and warm provider reports with stage timings, counts, overlap and scope limitations` | 2026-09-05 | `docs/roadmap/acceptance/evidence/AR-403-recall-performance-20260905.json:1-89` |
| 3 | command-output | `Warm report and unchanged staffing/hiring-gate scope` | 2026-09-05 | `docs/roadmap/acceptance/evidence/AR-403-recall-performance-20260905.json:90-170` |
| 3 | file | `Recall remains candidate evidence passed to staffing; cache reuse does not accept teams` | 2026-09-05 | `agency_runtime/core/workforce/inference.py:2600-2680` |

## Verification

| Criterion | Verdict | Verifier run | Evidence digest | Observed | Reason |
|---|---|---|---|---|---|

## Builder notes

Tests use deterministic provider replies; they are not live staffing claims.
AR-400 separately owns installation and all-host smoke evidence.

