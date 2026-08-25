---
title: "AR-266: Recall the complete workforce with dense hybrid retrieval"
status: in_progress
category: roadmap
created: 2026-08-24
updated: 2026-08-24
tags: [workforce, routing, embeddings, retrieval, inference]
related:
  - docs/roadmap/handoffs/issue-AR-266.md
  - docs/roadmap/issue-AR-265-contextual-turn-classification.md
  - docs/decisions/0083-use-capability-indexed-recall-and-bounded-inference.md
  - docs/decisions/0118-require-inference-owned-staffing.md
  - docs/decisions/0121-gate-deterministic-recall-without-selection-authority.md
  - docs/decisions/0163-resolve-contextual-turns-from-transcript-free-subjects.md
  - docs/decisions/0164-use-dense-embeddings-only-for-workforce-recall.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: workforce
issue_id: AR-266
priority: p0
tracker_url: null
depends_on: []
blocks: []
---

# AR-266: Recall the complete workforce with dense hybrid retrieval

## Problem

The active workforce recruiter does not inspect the complete governed roster.
For each inferred work unit, deterministic typed recall orders candidates by
coverage breadth and stable identity, then truncates the detail-card universe
to 24. The inference recruiter may select only from those cards. This protects
the recruiter from a roughly 273-card prompt, but a capable specialist outside
the first 24 is invisible and may be misreported as a workforce gap.

The defect is general classification and retrieval, not the literal phrase
`what's next?`. AR-265 now supplies a transcript-free subject for contextual
turns; workforce recall must use that current-turn subject to find relevant
specialists before inference decides the final staffing plan.

## Current state

- `_typed_shortlists` scans all enabled contracts but
  `_bounded_typed_candidates` retains at most 24 candidates per work unit.
- `allowed_candidate_ids` is exactly the resulting detail-card set, so the
  recruiter cannot recover a specialist that recall omitted.
- The legacy semantic selector uses deterministic sparse metadata features and
  is not on the active workforce path.
- The Store's legacy `agent_embeddings` table lacks roster, contract,
  projection, model-revision, dimension, and normalization identity. Its rows
  are not safe production index evidence.
- Inference already owns final staffing through the configurable
  `workforce.recruiter` route, and the hard staffing verifier rejects invalid
  proposals after inference.
- Tracker creation is pending explicit outward authorization.

## Approach

Preserve the existing 24-card typed result as a guaranteed lane, not the
complete recruiter universe. Build a positive-only, versioned search document
for every enabled audited contract and combine typed recall, exact lexical
matches, learned dense similarity, and bounded hard-negative evidence through
deterministic reciprocal-rank fusion. The union is additive: no hybrid score
may remove or reorder the baseline typed IDs. Bound the expanded detail-card
document by serialized bytes and a defensive row ceiling rather than treating
24 as the total candidate ceiling.

Create a query per inferred work unit from the current request, typed unit
fields, and AR-265's closed transcript-free subject hints. Do not include raw
prior messages, specialist slugs, trace identifiers, or historical prose. Run
query retrieval on every routed turn. Rebuild roster vectors only when the
roster fingerprint, contract-card hash, projection version, embedding model
revision, dimensions, or normalization identity changes.

Require an explicit `inference.routes.workforce.recall.embedding` profile with
`capability_class = "embeddings"`; a missing route disables learned recall
rather than falling through to the default text model. The existing
`workforce.recruiter` inference profile is the configurable reranker and sole
selection authority. Support `off`, `shadow`, and `additive` modes. Shadow is
the safe default while evaluation evidence is accumulated.

Use an exact in-process cosine scan at current roster scale and a bounded
process cache. Do not reuse or grandfather legacy `agent_embeddings` rows.
Reject stale, partial, zero, non-finite, or mixed-dimension vectors and fall
back explicitly to byte-equivalent typed-only behavior. Record source ranks,
universe count and digest, projection/model identity, latency, cache state,
and failure category without retaining raw vectors or query text.

Pass the expanded cards to the existing recruiter and unchanged staffing
verifier. Dense or lexical evidence is recall evidence only: it cannot select,
exclude, authorize hiring, grant mutation authority, or override exact
eligibility constraints.

## Dependencies

- AR-265 and ADR-0163 provide bounded current-turn subject context without
  replaying the session transcript.
- ADR-0083 governs capability-indexed bounded recall.
- ADR-0118 keeps substantive staffing inference-owned.
- ADR-0121 forbids promoting deterministic recall metrics to selection proof.

## Acceptance

- [ ] Versioned positive-only card documents exclude prompts, instructions,
      negative fields, audit findings, prior transcript, and raw vectors.
- [ ] Index identity binds the complete roster count and digest, recruiter
      fingerprint, card hashes, projection version, model revision,
      dimensions, and normalization.
- [ ] Every current-turn work unit receives a context-specialized query; a
      `what's next?` turn in two subjects produces distinct safe queries.
- [ ] The complete enabled roster is searched while all baseline typed IDs and
      their order are retained in additive mode.
- [ ] Expanded cards are byte-bounded and validated against the exact snapshot
      universe before recruiter inference.
- [ ] A separately configured embeddings model supplies learned vectors; the
      existing configurable recruiter model remains the sole reranker and
      selection authority.
- [ ] Missing, timed-out, malformed, stale, or mismatched embeddings preserve
      typed-only staffing and record explicit unavailable evidence.
- [ ] Dense evidence alone cannot create a semantic gap, hire a contractor,
      select an ineligible worker, or bypass the unchanged staffing verifier.
- [ ] Shadow evaluation proves 100-percent baseline retention, no category
      recall regression, zero forbidden/ineligible/disabled additions, zero
      stale-index reuse, and at least one predeclared recovered vocabulary gap.
- [ ] Warm turns do not re-embed the roster, use at most one batched query
      embedding request, and add no recruiter inference call.
- [ ] Focused tests, the named fast production spine, routing and decision
      conformance evaluations, documentation gates, and `git diff --check`
      pass before handoff.
- [ ] A same-repository tracker issue titled `[AR-266]` with label
      `epic:workforce` is created only after explicit authorization.
