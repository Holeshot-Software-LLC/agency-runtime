---
title: "Use learned embeddings only for additive workforce recall"
status: accepted
category: decisions
created: 2026-08-24
updated: 2026-08-24
tags: [workforce, embeddings, retrieval, inference, privacy]
related:
  - docs/roadmap/issue-AR-266-dense-hybrid-workforce-recall.md
  - docs/roadmap/handoffs/issue-AR-266.md
  - docs/decisions/0083-use-capability-indexed-recall-and-bounded-inference.md
  - docs/decisions/0118-require-inference-owned-staffing.md
  - docs/decisions/0121-gate-deterministic-recall-without-selection-authority.md
  - docs/decisions/0163-resolve-contextual-turns-from-transcript-free-subjects.md
  - SECURITY.md
  - docs/THREAT_MODEL.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
id: ADR-0164
type: decision
deciders: [maintainers]
---

# ADR-0164: Use learned embeddings only for additive workforce recall

## Context

The workforce recruiter currently sees at most 24 typed candidates per work
unit. That bound protects inference context but can hide a relevant specialist
whose terminology does not overlap the typed requirement vocabulary. Sending
every governed card to the recruiter recreates the prompt-size and spurious-gap
failures that motivated bounded recall. The existing dependency-free sparse
semantic selector does not provide learned semantic recall and is not on the
active workforce route.

Embeddings can improve recall, but their similarity scores are not staffing
decisions, calibrated confidence, safety filters, or execution authority.
Remote embeddings also create an additional provider-egress boundary, and the
legacy Store table cannot prove which exact cards and model produced its rows.

## Decision

Use learned embeddings only as an additive candidate-recall lane. Preserve the
existing typed candidates and their order, fuse lexical and dense discoveries
through deterministic reciprocal-rank fusion, and pass the byte-bounded union
to the existing inference recruiter. A separately configured recall-reranker
profile may order only the complete offered discovery set: it cannot drop,
invent, select, or hire a worker. The existing recruiter remains the sole
staffing selection authority; the unchanged staffing verifier remains the
final eligibility and safety veto.

Require separately and explicitly mapped `workforce.recall.embedding` and
`workforce.recall.reranker` routes. The former declares the `embeddings`
capability and the latter declares `text`; neither inherits a generic default
route. Provide `off`, `shadow`, and `additive` modes, with shadow as the initial
default. Recall uses an independent fixed two-call evidence budget, so shadow
cannot consume planner, recruiter, repair, or critic capacity. Provider
failure or invalid evidence degrades to the existing typed behavior and cannot
generate a hiring gap.

Embed only a versioned allowlist of positive governed card fields. Keep
negative suitability, authority, host, platform, tool, audit, employment,
composition, version, and hash data as exact filters or identity. Never embed
raw prompts, instructions, prior messages, trace metadata, source URLs, audit
findings, or stored outcomes. Current-turn queries may use the current request,
typed unit fields, and the closed AR-265 subject projection, but no transcript
or sticky specialist identity.

At current scale, use exact cosine scan and a bounded process cache. Bind every
cached catalog to the full roster digest, recruiter fingerprint, contract card
hashes, projection version, provider, exact actual-model revision, dimensions,
and normalization. A missing actual-model receipt is typed-only and cannot
populate or reuse the cache. Do not reuse the legacy `agent_embeddings` table;
persistence requires a future schema whose manifest enforces the same identity.

## Consequences

The recruiter can see semantically relevant specialists beyond the original
24-card typed window without paying the full-roster prompt cost. Contextual
questions are rerouted against the subject of the active work on every turn,
while roster vectors are reused only under exact identity.

Embedding availability becomes optional infrastructure with explicit egress,
latency, cache, and evidence obligations. Shadow evaluation is required before
additive mode may affect active detail cards. Dense scores are diagnostic
source ranks only and must not be described as selection proof.

## Alternatives

Sending the complete roster to inference was rejected because it restores the
context and spurious-gap failure. Selecting the nearest vector directly was
rejected because it transfers staffing authority to an uncalibrated retrieval
score. Reusing the sparse legacy selector was rejected because it duplicates
lexical metadata matching rather than adding learned semantics. Bundling a
local embedding runtime was rejected for the first slice because its model,
licensing, platform, and Python-version burden is disproportionate. Reusing
the legacy Store table was rejected because its rows lack sufficient identity
and staleness controls.
