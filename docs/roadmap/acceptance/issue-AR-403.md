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
| 3 | file | `After recall and recruiter, every proposal still runs verify_staffing and plan-policy checks; rejected teams fail and strict mode still invokes its critic` | 2026-09-05 | `agency_runtime/core/workforce/inference.py:4830-4948` |
| 3 | file | `Hiring still runs its independent critic and handles rejection before security review` | 2026-09-05 | `agency_runtime/core/workforce/hiring.py:2420-2486` |
| 3 | file | `Security review and bounded unsafe-repair loop still gate worker creation; no cache condition bypasses them` | 2026-09-05 | `agency_runtime/core/workforce/hiring.py:2487-2564` |

## Verification

| Criterion | Verdict | Verifier run | Evidence digest | Observed | Reason |
|---|---|---|---|---|---|
| 1 | satisfied | `AR-403.1-20260905-2cfc473d` | `0a7dd07006cd8dc3b67b4e5cc378f857b6979e0313de4753e714dbc118b8e753` | 2026-09-05 | The subprocess test in tests/test_persistent_hybrid_recall_cache.py asserts embedding counts of three then one and identical candidates; catalog_vector_cache.py decodes exact float64 vectors without renormalization. |
| 2 | satisfied | `AR-403.2-20260905-af39a614` | `5f049d70acaf8b414bb48025511c5edf1c25c4a4ddb9b46e5b5c523e79ea2667` | 2026-09-05 | The invalidation and unsafe-target tests demonstrate rebuilding or rejecting stale vectors, while catalog_vector_cache.py catches read, write and invalidation faults so they do not block valid recall. |
| 3 | satisfied | `AR-403.3-20260905-e65561cc` | `cdcecebd246080716ebb451392c2465235497c37c8748bebb33a5b153bec7dc6` | 2026-09-05 | AR-403-recall-performance-20260905.json records current live cold/warm timings, counts, cache hits and explicit limitations; inference.py and hiring.py retain staffing verification, policy checks, strict critic, hiring critic and security gates. |

## Builder notes

The first isolated verdict for criterion 3 was absent because its production
wiring was not included in the excerpts. Commit 606065f2 preserves that judgment.
The builder now cites the actual call sites; the changed evidence awaits a fresh
verifier judgment and does not inherit the old digest.

Tests use deterministic provider replies; they are not live staffing claims.
AR-400 separately owns installation and all-host smoke evidence.
