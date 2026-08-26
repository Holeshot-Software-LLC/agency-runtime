---
title: "AR-303: Bound full-roster embedding requests"
status: in_progress
category: roadmap
created: 2026-08-26
updated: 2026-08-26
tags: [workforce, embeddings, retrieval, reliability, inference]
related:
  - docs/roadmap/issue-AR-266-dense-hybrid-workforce-recall.md
  - docs/roadmap/issue-AR-286-configure-bounded-embedding-dimensions.md
  - docs/roadmap/issue-AR-287-bind-host-hook-timeouts-to-inference-budgets.md
  - docs/roadmap/issue-AR-297-complete-unattended-container-bootstrap.md
  - docs/roadmap/handoffs/issue-AR-297.md
  - docs/decisions/0164-use-dense-embeddings-only-for-workforce-recall.md
  - docs/decisions/0175-batch-complete-embedding-input-sets.md
  - agency_runtime/core/workforce/embedding_provider.py
  - agency_runtime/core/workforce/hybrid_recall.py
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: workforce
issue_id: AR-303
priority: p0
tracker_url: null
depends_on: [AR-266, AR-286]
blocks: [AR-297]
---

# AR-303: Bound full-roster embedding requests

## Problem

The AR-297 exact config requests 4,096-dimensional embeddings for the complete
workforce. A 263-card catalog plus one query requires 1,081,344 scalar values,
which exceeds the unchanged 1,000,000-value aggregate safety bound. The recall
layer previously made one combined provider call, so it failed locally before
the configured embedding provider could be reached.

## Current state

- The candidate implementation validates the complete logical input set before
  transport, then divides it into at most two ordered scalar-safe input batches.
- At 4,096 dimensions the per-call ceiling is 243 inputs after reserving JSON
  row/container nodes. The exact 263-card regression uses batches of 243 and 21
  including its query; a warm cache still
  embeds only the query in one call.
- All batches must report the same exact actual model and dimensions. Any
  provider failure, count mismatch, dimension drift, or model drift discards
  the whole logical result, leaves the catalog cache empty, and returns the
  unchanged typed-only recall lane.
- The independent cold recall budget is three calls: at most two embeddings and
  one reranker. Generated host timeouts account for both embedding calls.
- Focused warning-strict coverage currently passes 139 tests. The first private
  live preflight reached LiteLLM rather than failing the scalar bound, then
  received 401 because the direct process did not inherit the configured
  `LITELLM_API_KEY`. A one-input check using the running gateway's existing
  protected service credential passed at exactly 4,096 dimensions. The
  authenticated full preflight then reached a 200 response but rejected it
  because 244 rows of 4,096 values plus JSON row/container structure exceeded
  the parser's separate one-million-node cap. The batch limiter now reserves
  those nodes and admits at most 243 rows. Authenticated trace
  `d055d5b4-4bb9-4f6a-993c-5364b27c9e2b` then applied both embedding batches
  with exact `qwen3-embedding` identity and applied the exact Mistral reranker.
  Staffing continued to the recruiter, where separate AR-304 semantic failures
  remained.
- Tracker creation is prohibited by the active task.

## Approach

Prevalidate every input count, text size, and aggregate byte bound before the
first provider call. Compute the per-request row ceiling only from the explicit
configured dimension and the existing scalar bound. Reject a logical request
that would require more than two calls before transport. Never split, slice,
pad, or reshape a returned vector.

Aggregate only content-free receipts across successful batches. Preserve exact
input order and require one model/dimension identity across all batches before
the cache can commit. Keep dimensions-zero profiles on the existing single-call
path because the runtime cannot safely infer a provider-native width.

## Dependencies

- AR-266 owns additive recall authority and typed-only fallback.
- AR-286 owns the exact configured dimension contract.
- AR-287 owns host timeout parity with every statically reachable call.
- Tracker creation requires separate outward-write authorization.

## Acceptance

- [x] A 263-card, 4,096-dimensional cold request uses two ordered scalar-safe
      embedding calls and a warm request uses one.
- [x] Complete logical input bounds are checked before any provider call.
- [x] Second-batch provider failure, dimension drift, and model drift are
      atomic, content-free, uncached typed-only outcomes.
- [x] The per-call row limit satisfies both the scalar-value cap and bounded
      JSON structural-node cap.
- [x] Recall and host timeout budgets cover two embedding calls plus one
      reranker without consuming staffing inference capacity.
- [x] Focused warning-strict tests and Ruff checks pass.
- [x] One authenticated exact-config private preflight applies the two-batch
      embedding route and persists correlated evidence.
- [ ] The named repository gates pass on the checkpointed implementation.
- [ ] A same-repository tracker is created and linked after explicit
      authorization.
