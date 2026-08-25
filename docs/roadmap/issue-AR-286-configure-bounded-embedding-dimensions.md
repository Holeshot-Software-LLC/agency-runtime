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

- The embedding profile records provider, model, capability, URL, credential
  indirection, transport, and timeout, but no requested output dimension.
- The locally available embedding model returns 4,096 values by default and
  supports a provider-native 1,024-dimension response when requested.
- Agency correctly rejects a complete-roster batch whose scalar count exceeds
  the existing safety bound. No bound was raised and no vector was sliced.
- Reranking is independent of this defect; its separately routed text profile
  remains subject to the existing closed response schema.
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

## Acceptance

- [ ] `dimensions` defaults to zero and zero omits the provider request field.
- [ ] Only embedding profiles on `ollama`, `openai-compatible`, or `litellm`
      accept a nonzero bounded value.
- [ ] Ollama and OpenAI-compatible/LiteLLM embedding requests receive the
      configured nonzero dimension.
- [ ] Every returned vector must exactly match the requested dimension;
      unsupported, stripped, or mismatched requests preserve typed-only recall.
- [ ] Catalog identity changes when the requested dimension changes.
- [ ] Existing per-vector and aggregate scalar bounds remain unchanged, and no
      client-side slicing or padding is introduced.
- [ ] Focused configuration, provider, cache-identity, fallback, and receipt
      regressions pass before live shadow evaluation.
- [ ] Tracker creation and linkage remain pending separate authorization.
