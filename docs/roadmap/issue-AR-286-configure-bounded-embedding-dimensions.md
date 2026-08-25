---
title: "AR-286: Configure bounded embedding dimensions"
status: in_progress
category: roadmap
created: 2026-08-25
updated: 2026-08-25
tags: [workforce, embeddings, retrieval, inference, configuration]
related:
  - docs/roadmap/issue-AR-266-dense-hybrid-workforce-recall.md
  - docs/roadmap/handoffs/issue-AR-266.md
  - docs/roadmap/reference-workforce-inference-stages.md
  - docs/decisions/0164-use-dense-embeddings-only-for-workforce-recall.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: workforce
issue_id: AR-286
priority: p0
tracker_url: null
depends_on: [AR-266]
blocks: []
---

# AR-286: Configure bounded embedding dimensions

## Problem

AR-266 validates both each embedding vector and the total scalar count in one
complete-roster batch. Some otherwise compatible embedding models default to
4,096 dimensions. At the current roster size, that valid per-vector width can
exceed Agency's unchanged one-million-scalar batch bound. The provider can
produce a smaller native projection, but Agency's inference-profile schema has
no way to request it, so learned recall falls back to typed-only behavior.

Client-side slicing is not a safe substitute. Truncating an already-produced
vector is not the provider's documented projection and would make similarity,
cache identity, and model evidence ambiguous.

## Current state

- Commit `2bea0c76` adds the bounded `dimensions` profile field, provider-native
  request projection, exact-width response enforcement, cache identity, and
  typed-only fallback. Its ledger commit is `9adee235`.
- The local Agency-only configuration now requests 1,024 dimensions from
  `qwen3-embedding:latest` through Ollama and routes recall reranking to
  `qwen3-14b-abliterated:latest`. Dense recall remains `shadow`.
- A direct live embedding call returned one 1,024-value vector and identified
  the requested model as the actual answering model. A direct reranker call
  returned a complete schema-valid two-candidate ordering with its model
  identity sourced from the response body.
- A bounded four-host-labelled integration smoke ran the exact AR-266 hybrid
  path for Codex, Claude, Hermes, and OpenClaw. All four recorded applied
  embedding and reranker attempts; Codex and Claude were evaluator-only and
  did not invoke either native host or OAuth.
- The first host embedded the complete 278-worker catalog plus one query; the
  other three reused the exact model-and-dimension-bound catalog and embedded
  one new query each. Every host observed 1,024 dimensions and 16 additions.
- Existing per-vector and one-million-scalar bounds remain unchanged. No
  vector was sliced or padded.
- Tracker creation is pending explicit authorization. No outward tracker write
  is authorized by this local package.

## Approach

Add an optional integer `dimensions` field to inference profiles and their
projected provider entries. `dimensions: 0` is the default and omits the field
from the provider request. A nonzero value is valid only for an `embeddings`
capability profile using `ollama`, `openai-compatible`, or `litellm`; text,
code, CLI, and unsupported-provider profiles reject it during configuration
validation.

Send a nonzero value through the provider's native embedding request and
require every returned vector to have exactly that dimension. Provider
rejection, parameter stripping, or a mismatched response records unavailable
learned recall and preserves the byte-equivalent typed-only lane. Do not slice,
pad, or otherwise reshape vectors in Agency.

Include the configured dimension in catalog/cache identity so vectors produced
under different projections cannot be reused together. Preserve all existing
input-count, per-vector dimension, scalar-count, byte, timeout, and response
bounds unchanged.

## Dependencies

- AR-266 owns dense hybrid workforce recall, typed-lane preservation, and live
  shadow evaluation.
- ADR-0164 keeps embeddings additive and non-authoritative.
- The selected provider and model must implement a native dimensions option;
  absence or removal of that support must fail to typed-only recall.
- Tracker creation requires separate authorization.

## Verification evidence

- Regression-first artifact
  `/tmp/ar286-regression-red.txt` has SHA-256
  `8e4fe65511b6eaad6d41d3aef49206b3f373f88467c1ae5b5e66dcab8184b54b`
  and contains the expected 12 failures before implementation.
- 167 focused configuration, embedding-provider, cache-identity, fallback,
  receipt, and workforce inference tests pass with warnings treated as errors.
- Independent review returned GO with no Critical, High, or Medium findings.
- Full Ruff check and format-check, documentation checks, and
  `git diff --check` passed before the implementation checkpoint.
- Live local embedding, reranker, and four-host-labelled shadow-path smokes
  passed on 2026-08-25. They do not prove native Codex/Claude activation or
  authorize additive recall.

## Acceptance

- [x] `dimensions` defaults to zero and zero omits the provider request field.
- [x] Only embedding profiles on `ollama`, `openai-compatible`, or `litellm`
      accept a nonzero bounded value.
- [x] Ollama and OpenAI-compatible/LiteLLM embedding requests receive the
      configured nonzero dimension.
- [x] Every returned vector must exactly match the requested dimension;
      unsupported, stripped, or mismatched requests preserve typed-only recall.
- [x] Catalog identity changes when the requested dimension changes.
- [x] Existing per-vector and aggregate scalar bounds remain unchanged, and no
      client-side slicing or padding is introduced.
- [x] Focused configuration, provider, cache-identity, fallback, and receipt
      regressions pass before live shadow evaluation.
- [ ] Tracker creation and linkage remain pending separate authorization.
