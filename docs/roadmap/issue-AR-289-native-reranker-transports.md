---
title: "AR-289: Support native reranker transports"
status: in_progress
category: roadmap
created: 2026-08-25
updated: 2026-08-25
tags: [workforce, reranking, retrieval, inference, providers]
related:
  - docs/roadmap/handoffs/issue-AR-289.md
  - docs/roadmap/issue-AR-266-dense-hybrid-workforce-recall.md
  - docs/roadmap/issue-AR-286-configure-bounded-embedding-dimensions.md
  - docs/roadmap/reference-workforce-inference-stages.md
  - docs/decisions/0164-use-dense-embeddings-only-for-workforce-recall.md
  - docs/decisions/0171-separate-native-and-structured-reranker-transports.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: provider-runtime
issue_id: AR-289
priority: p1
tracker_url: null
depends_on: [AR-266]
blocks: []
---

# AR-289: Support native reranker transports

## Problem

Dense workforce recall can already obtain embeddings from Ollama,
OpenAI-compatible endpoints, and LiteLLM. Its recall-reranker route, however,
always invokes a generative text model through the structured-provider seam.
That correctly supports local chat models, LiteLLM, API-key chat providers,
and Codex or Claude subscription CLIs, but it cannot call a purpose-built
reranking API such as Jina's `/v1/rerank` endpoint.

Pointing a text profile at a native reranker is unsafe: Agency would append a
chat-completions path and send the wrong request schema while configuration
still appeared superficially valid. Operators need an explicit native
capability whose transport, evidence, and failure behavior are validated before
the route becomes active.

## Current state

- `workforce.recall.embedding` requires an explicit `embeddings` profile and
  already supports Jina's OpenAI-compatible embedding endpoint.
- `workforce.recall.reranker` requires an explicit `text` profile and expects a
  schema-constrained generative response containing every offered ID once.
- Missing or invalid recall routes preserve the byte-equivalent typed candidate
  lane, and the recruiter remains the sole staffing selector.
- The supplied Jina embedding and reranker endpoints both answered a bounded
  credential-redacted live probe on 2026-08-25, but no credential or Jina route
  was persisted.
- Tracker creation is pending explicit authorization. No outward tracker write
  is authorized by this local package.

## Approach

Add a `rerank` inference capability and a narrowly scoped `jina` inference
adapter. Keep the existing `text` route valid so local generative models,
LiteLLM, direct chat APIs, and Codex or Claude subscriptions remain unchanged.
The recall resolver accepts either capability only for
`workforce.recall.reranker` and dispatches each through its own typed transport.

The native transport sends one bounded query and every offered positive-only
candidate document to `/v1/rerank`, requests all results, and requires a
complete permutation of zero-based candidate indices. It records content-free
provider/model/count/latency evidence and converts the validated permutation to
Agency IDs. It does not trust scores as confidence, eligibility, staffing, or
execution authority.

Require HTTPS for credentialed remote endpoints, environment-based credentials,
bounded request and response sizes, no redirects, exact actual-model identity,
finite scores, and fail-closed response validation. Any transport error,
missing/duplicate/out-of-range index, partial result, model-identity failure, or
timeout preserves the unchanged typed lane.

## Dependencies

- AR-266 owns dense recall, typed-lane preservation, and the two-call recall
  budget.
- ADR-0164 keeps learned recall additive and non-authoritative.
- The structured text reranker remains the compatibility path for providers
  without a native rerank operation.
- Tracker creation requires separate authorization.

## Verification evidence

- Added a stage-scoped `jina` adapter and `rerank` capability. Persisted config
  rejects native reranker defaults, non-reranker routes, `thinking_level`, and
  mismatched adapter/capability combinations while preserving structured
  `text` reranker profiles.
- Added a bounded no-redirect Jina transport for root, `/v1`, or exact
  `/v1/rerank` base URLs. It resolves literal or environment-backed bearer
  credentials, requires HTTPS for credentialed remote endpoints, permits
  keyless literal loopback, bounds input/output, requests all documents, and
  records no query, document, score, or credential content in receipts.
- Native response validation requires the exact complete index permutation,
  finite descending numeric scores, and a text actual-model receipt. The
  validated order is projected back into each work unit without persisting or
  interpreting scores as staffing confidence.
- The existing structured reranker branch remains byte-path compatible for
  Ollama/local chat models, LiteLLM, direct chat API keys, and Codex/Claude
  subscription CLIs. A focused regression proves it never dispatches the
  native invoker.
- Focused configuration, transport, and workforce integration verification:
  `174 passed` with warnings as errors. The named fast production spine plus
  the new provider file passed `856` tests with `20` expected skips. Dashboard
  verification passed `134` tests. Whole-repository Ruff lint and format
  checks passed for `691` Python files; documentation validation passed for
  `807` Markdown files.
- Routing evaluation passed every configured gate. Decision conformance passed
  its baseline and killed all `160/160` curated mutations with zero survivors;
  its report confirmed the source tree was unchanged.
- The supplied Jina endpoints answered a separate credential-redacted live
  probe before implementation. This branch did not persist the key, install an
  unpublished build, or claim a live post-implementation Jina route.

## Acceptance

- [x] A Jina inference profile can explicitly declare `capability_class:
      rerank` without becoming eligible for generative inference stages.
- [x] Native reranking sends one bounded query and the complete offered
      candidate set to `/v1/rerank` with credentials resolved from an
      environment variable.
- [x] Only a complete exact permutation with an exact actual-model receipt is
      accepted; malformed or partial results preserve typed-only recall.
- [x] Native scores can order recalled candidates but never become staffing
      confidence, eligibility, hiring, or execution authority.
- [x] Existing text rerankers on Ollama, LiteLLM, direct chat APIs, and
      Codex/Claude subscription transports remain backward-compatible.
- [x] Focused configuration, provider, inference, fallback, security, and
      receipt tests pass with warnings treated as errors.
- [ ] Tracker creation and linkage remain pending separate authorization.
