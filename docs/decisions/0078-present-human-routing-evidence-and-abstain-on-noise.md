---
title: "Present human routing evidence and abstain on weak heuristic noise"
status: superseded
category: decisions
created: 2026-07-21
updated: 2026-09-05
tags: [routing, observability, headers, heuristics]
related:
  - docs/decisions/0222-retire-superseded-live-routing-contract.md
  - docs/roadmap/issue-AR-115-live-routing-trust.md
  - docs/decisions/0001-layered-specialist-routing.md
  - docs/decisions/0027-authoritative-runtime-evidence-traces.md
  - docs/decisions/0030-versioned-quantitative-evaluation-gates.md
  - docs/worklog/README.md
supersedes: []
superseded_by: docs/decisions/0222-retire-superseded-live-routing-contract.md
id: ADR-0078
type: decision
deciders: [maintainers]
---

# ADR-0078: Present human routing evidence and abstain on weak heuristic noise

Superseded by ADR-0222. The original text below is historical: deterministic
staffing fallback and the six-field header must not be restored. Current live
selection and evidence obligations remain under AR-119/AR-125; this retirement
does not certify their success.

## Context

Agency stores bounded machine codes so current-turn routing evidence can be
validated exactly. Printing those codes directly in every answer is auditable
but not useful to a person. Separately, deterministic metadata embeddings can
produce small positive scores for unrelated domains. When inference is absent
or unavailable, treating every positive score as a match can load a confidently
wrong specialist.

## Decision

Keep raw reason and effect codes in the authoritative durable routing receipt.
Project those codes deterministically into concise plain-English Why and How
header lines. Unknown future codes receive a readable mechanical rendering, so
new evidence remains visible without allowing authored prose to override it.

Heuristic token fallback must meet an absolute minimum signal as well as its
existing relative-score test. Below that floor it abstains, allowing the
always-resident orchestrator and chief of staff to handle the request. The
deterministic path selects at most two compatible specialists and only when
each survives the relative floor. An inference-provider result remains the
semantic proposal when inference is configured, but it must meet the configured
confidence floor before caching, prompt hydration, or activation.

## Consequences

- People can understand the header without losing machine-verifiable evidence.
- Completion validation still compares all six fields with current-turn facts.
- Low-signal prompts prefer a transparent coordinator fallback over a
  domain-irrelevant specialist.
- A model-selected candidate below the operator's confidence floor is a real
  abstention, not a prompt that is quietly loaded behind advisory wording.
- Evaluation must include forbidden specialists and real prompt regressions,
  not only aggregate scores over a synthetic catalog.

## Alternatives

- **Remove Why and How.** Rejected because users lose routing visibility.
- **Permit free-form authored explanations.** Rejected because they can drift
  from the recorded turn.
- **Always trust deterministic embedding order.** Rejected because the observed
  clinical and geography selections were low-score collisions.
- **Require inference for every installation.** Rejected because inference is
  optional unless the operator configures it as authoritative.
