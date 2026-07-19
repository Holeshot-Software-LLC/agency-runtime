---
title: "AR-84: Give the semantic judge bounded full agent cards"
status: in_progress
category: roadmap
created: 2026-07-17
updated: 2026-07-17
tags: [routing, semantic-judge, metadata, prompts, performance]
related:
  - docs/decisions/0030-versioned-quantitative-evaluation-gates.md
  - docs/decisions/0062-isolate-directives-and-route-units-first.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: routing
issue_id: AR-84
priority: p1
tracker_url: "https://github.com/Holeshot-Software-LLC/agency-runtime/issues/80"
depends_on: [AR-11, AR-82]
blocks: []
---

# AR-84: Give the semantic judge bounded full agent cards

## Problem

The semantic judge received only each slug and the first 80 description
characters. It could not reliably distinguish neighboring specialists by
division, capabilities, categories, or tool affinity.

## Current state

The judge-card contract is being expanded with deterministic bounded metadata
while excluding raw prompt bodies and preserving the provider response schema.
Final size, routing, and integrated verification remain in progress.

## Approach

Render concise structured cards from the already-approved selector projection:
identity, division, description, categories, capabilities, and tool affinity.
Bound every field and the total candidate list before any provider call. Keep
selection validation restricted to the exact prompted candidate identities.

## Dependencies

AR-11 owns quantitative routing gates and AR-82 removes the unit-level recall
ceiling before semantic reranking.

## Acceptance

- [ ] Semantic candidates include all approved routing metadata fields.
- [ ] Field and total prompt sizes remain deterministically bounded.
- [ ] Raw prompt bodies are never included in the judge request.
- [ ] Existing provider and candidate-validation contracts remain compatible.
- [ ] Full routing, performance, and merged-install gates pass.
