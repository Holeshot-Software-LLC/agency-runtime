---
title: "Batch complete embedding input sets within a bounded recall budget"
status: accepted
category: decisions
created: 2026-08-26
updated: 2026-08-26
tags: [workforce, embeddings, retrieval, inference, reliability]
related:
  - docs/roadmap/issue-AR-303-bound-full-roster-embedding-requests.md
  - docs/roadmap/issue-AR-266-dense-hybrid-workforce-recall.md
  - docs/roadmap/issue-AR-286-configure-bounded-embedding-dimensions.md
  - docs/roadmap/issue-AR-287-bind-host-hook-timeouts-to-inference-budgets.md
  - docs/roadmap/issue-AR-297-complete-unattended-container-bootstrap.md
  - docs/roadmap/handoffs/issue-AR-297.md
  - docs/decisions/0164-use-dense-embeddings-only-for-workforce-recall.md
  - agency_runtime/core/workforce/embedding_provider.py
  - agency_runtime/core/workforce/hybrid_recall.py
  - docs/THREAT_MODEL.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
id: ADR-0175
type: decision
deciders: [maintainers]
---

# ADR-0175: Batch complete embedding input sets within a bounded recall budget

## Context

ADR-0164 originally assigned dense recall one embedding call and one reranker
call. That topology works when the complete logical embedding matrix fits the
per-call scalar bound. AR-297's exact 4,096-dimensional profile does not: the
governed roster plus a query exceeds 1,000,000 scalar values even though each
individual vector, input, and byte count is valid.

Raising the scalar bound would weaken a memory and response-size guard. Reducing
the configured dimension would change an owner-approved model contract.
Returning only a catalog prefix would make recall incomplete. Slicing returned
vectors would corrupt their geometry and violate ADR-0164.

## Decision

Treat a cold catalog plus its queries as one logical embedding input set, but
permit at most two ordered provider requests when an explicit configured
dimension proves each request remains within the existing scalar bound.
Validate the full logical input count and bytes before the first request.
Profiles with an unknown provider-native dimension retain the single-request
behavior; Agency does not guess their width.

Do not slice, pad, truncate, or otherwise reshape vectors. Every batch must
return its exact row count, configured dimension, requested identity, and one
consistent actual-model identity. A failure or drift in any batch discards all
partial vectors, leaves the cache unchanged, and produces the existing
typed-only outcome. The aggregate receipt contains only bounded counts,
identity, status, and summed capped latency.

Refine the independent recall budget to three calls for a cold catalog: two
embedding requests and one reranker. A warm catalog remains one embedding call
plus one reranker. This budget remains separate from planner, recruiter,
repair, critic, and hiring budgets. Host hook timeout calculation must cover
both possible embedding timeouts.

This decision refines ADR-0164's fixed two-call budget. It does not change
ADR-0164's additive-only authority, positive-field projection, exact cosine
scan, typed baseline, cache identity, or prohibition on vector reshaping.

## Consequences

- Complete 4,096-dimensional workforce recall can remain within the unchanged
  scalar cap without changing the approved model or dimension.
- Cold recall can spend one additional bounded local provider call and host
  timeouts increase accordingly.
- Partial provider work is never cached or treated as recall evidence.
- Configurations needing more than two batches fail before transport and must
  receive a separately reviewed capacity decision.

## Alternatives

- **Raise the aggregate scalar limit.** Rejected because it weakens the memory
  and response-size boundary for every provider call.
- **Lower the configured dimension automatically.** Rejected because it changes
  the exact operator-selected embedding contract.
- **Embed only a roster prefix.** Rejected because it silently makes complete
  workforce recall incomplete and order-dependent.
- **Slice or combine vectors client-side.** Rejected because it changes learned
  geometry and cannot preserve provider semantics.
- **Allow unbounded batching.** Rejected because latency, provider cost, and
  host lease requirements would no longer be statically bounded.
