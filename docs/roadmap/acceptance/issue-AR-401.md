---
title: "AR-401 acceptance verification record"
status: active
category: roadmap
created: 2026-09-05
updated: 2026-09-05
tags: [acceptance, verification, staffing]
related:
  - docs/roadmap/issue-AR-401-enforce-preflight-deadlines-at-provider-boundaries.md
  - docs/roadmap/handoffs/issue-AR-400.md
supersedes: []
superseded_by: null
type: acceptance-verification
issue_id: AR-401
candidate_commit: 1de05aead322dbbf359a0a5f3ab19dcbb7cdeff9
evidence_cutoff: 2026-09-05
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/666
---

# AR-401 acceptance verification record

Candidate is the implementation merged through PR #669. Builder rows identify
observable artifacts; the isolated verifier alone supplies judgments.

## Builder evidence

| Criterion | Kind | Artifact | Observed | Source |
|---|---|---|---|---|
| 1 | test | `Real creator, critic and security sequence cannot spend a fresh timeout per stage; leaves exhaustion account and no pending commit` | 2026-09-05 | `tests/test_preflight_provider_deadline.py:117-168` |
| 1 | test | `Fallback providers share one budget and stop before the third call` | 2026-09-05 | `tests/test_preflight_provider_deadline.py:237-282` |
| 1 | file | `Shared absolute deadline reserves close time, cannot be extended and resets on exit` | 2026-09-05 | `agency_runtime/core/provider_deadline.py:1-68` |
| 2 | test | `Actual structured, embedding and native-reranking HTTP transports clamp time and reject expiry` | 2026-09-05 | `tests/test_preflight_provider_deadline.py:65-114` |
| 2 | test | `Native CLI preparation is charged before launch, semantic repairs reuse one cutoff` | 2026-09-05 | `tests/test_preflight_provider_deadline.py:171-234` |
| 2 | test | `Nested and concurrent contexts do not extend or leak deadline state` | 2026-09-05 | `tests/test_preflight_provider_deadline.py:285-296` |
| 2 | file | `bounded_preflight_route wraps the complete synchronous route in one ContextVar deadline with ten-second close margin` | 2026-09-05 | `agency_runtime/core/provider_deadline.py:1-68` |
| 2 | file | `Production route is decorated with bounded_preflight_route` | 2026-09-05 | `agency_runtime/core/selector/pipeline.py:1975-2004` |
| 2 | file | `All inference-stage provider calls clamp and test the shared context deadline` | 2026-09-05 | `agency_runtime/core/workforce/inference.py:1747-1811` |
| 2 | test | `Actual preflight invokes real routing/planning and consumes exactly the shared 65-second budget` | 2026-09-05 | `tests/test_preflight_provider_deadline.py:20-63` |
| 3 | test | `Actual preflight writes terminal receipt and no open trace when provider consumes its deadline` | 2026-09-05 | `tests/test_preflight_provider_deadline.py:20-63` |
| 3 | test | `Exhausted real hiring cannot commit incomplete pending workers` | 2026-09-05 | `tests/test_preflight_provider_deadline.py:117-168` |

## Verification

| Criterion | Verdict | Verifier run | Evidence digest | Observed | Reason |
|---|---|---|---|---|---|
| 1 | satisfied | `AR-401.1-20260905-e085b30d` | `88575b15da86a8cf5dea1f9cd191e52225d08fc5a9be37de4676b04e90c9fd5b` | 2026-09-05 | test_preflight_provider_deadline.py shows real hiring and fallback calls stop after two bounded calls and record hiring_lease_budget_exhausted; provider_deadline.py enforces a shared absolute cutoff. |
| 2 | satisfied | `AR-401.2-20260905-cb90d3c9` | `686398a40dce50e684f2817ccc3adf350e203a3fa0415226cdf540ececdc5446` | 2026-09-05 | provider_deadline.py scopes and resets one routing cutoff; test_preflight_provider_deadline.py covers planning, semantic repair, structured, embedding and reranking transports, nested deadlines, thread isolation and exception cleanup. |
| 3 | satisfied | `AR-401.3-20260905-c62c5275` | `4fa9eca315e3839f47ee0a90d4609195724216866b42921c9dac8c1086118ed3` | 2026-09-05 | tests/test_preflight_provider_deadline.py:20-63 asserts terminal preflight failure and a deadline receipt; lines 117-168 assert exhausted hiring is rejected, leaves the worker count unchanged, and produces no pending commit. |

## Builder notes

The first isolated verdict for criterion 2 was absent because its production
wiring was not included in the excerpts. Commit 606065f2 preserves that judgment.
The builder now cites the actual call sites; the changed evidence awaits a fresh
verifier judgment and does not inherit the old digest.

Tests use deterministic provider replies; they are not live staffing claims.
AR-400 separately owns installation and all-host smoke evidence.
