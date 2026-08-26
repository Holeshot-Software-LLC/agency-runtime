---
title: "Separate native and structured reranker transports"
status: accepted
category: decisions
created: 2026-08-25
updated: 2026-08-25
tags: [workforce, reranking, retrieval, inference, providers]
related:
  - docs/roadmap/issue-AR-289-native-reranker-transports.md
  - docs/roadmap/issue-AR-293-safe-inference-profile-config-operations.md
  - docs/roadmap/issue-AR-296-project-effective-inference-topology.md
  - docs/roadmap/issue-AR-266-dense-hybrid-workforce-recall.md
  - docs/decisions/0153-adopt-per-stage-inference-profile-routes.md
  - docs/decisions/0164-use-dense-embeddings-only-for-workforce-recall.md
  - SECURITY.md
  - docs/THREAT_MODEL.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
id: ADR-0171
type: decision
deciders: [maintainers]
---

# ADR-0171: Separate native and structured reranker transports

## Context

Agency's dense-recall reranker currently uses the same structured text seam as
planning and recruitment. That is a useful compatibility contract for local
chat models, LiteLLM, API-key chat providers, and authenticated Codex or Claude
CLIs. Purpose-built reranking services expose a materially different operation:
they accept one query and a document collection and return ranked indices and
scores rather than generated JSON text.

Treating those protocols as interchangeable would allow configuration to look
valid while the runtime calls the wrong endpoint and schema. It would also
tempt provider scores to leak into staffing confidence even though ADR-0164
keeps learned recall non-authoritative.

## Decision

Keep structured text reranking as an accepted compatibility transport and add
an explicit native `rerank` capability for operation-specific adapters. A
native adapter is eligible only for the recall-reranker route; it is never a
generic text default and cannot serve planner, recruiter, critic, hiring, or
security-review stages.

The first native adapter targets Jina's `/v1/rerank` contract. Send the complete
positive-only offered candidate set, request every result, and accept only an
exact permutation of the request indices with finite scores and an exact
actual-model receipt. Convert that permutation to candidate IDs locally. Scores
may determine order only; they are not persisted as calibrated evidence and do
not authorize selection, hiring, or execution.

Preserve the existing explicit-route requirement, independent two-call recall
budget, no-redirect HTTPS and credential rules, content and byte bounds,
content-free receipts, and typed-only fallback. Keep secrets in environment
indirection rather than provider URLs, command lines, or durable evidence.

## Consequences

Jina can provide both embeddings and native reranking without a local model or
generative API. Existing Ollama, LiteLLM, direct chat, and subscription profiles
continue through the unchanged structured text path. Future native reranker
adapters can share the same internal permutation contract without weakening
provider-specific wire validation.

The configuration vocabulary gains a capability and adapter that must remain
strictly stage-scoped. Native provider request/response parsing becomes another
remote egress boundary and requires dedicated bounds, security tests, and exact
model evidence.

## Alternatives

Pointing the existing OpenAI-compatible text adapter at `/v1/rerank` was
rejected because Agency would append `/v1/chat/completions` and send the wrong
schema. Replacing structured reranking entirely was rejected because it would
remove working local, LiteLLM, API-key, and subscription paths. A Jina-specific
special case inside workforce inference was rejected because transport parsing
and security bounds belong behind a typed provider seam. Using native scores as
staffing confidence was rejected because retrieval remains non-authoritative.
