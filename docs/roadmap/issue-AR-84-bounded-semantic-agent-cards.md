---
title: "AR-84: Give the semantic judge bounded full agent cards"
status: done
category: roadmap
created: 2026-07-17
updated: 2026-07-19
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

Judge cards now carry the complete approved routing projection under
deterministic per-field and aggregate bounds. Raw prompt bodies remain excluded,
and existing provider and candidate-validation schemas remain compatible. The
exact merged installation passes routing, delegation, full-roster, and latency
gates with complete semantic participation and recall.

## Approach

Render concise structured cards from the already-approved selector projection:
identity, division, description, categories, capabilities, and tool affinity.
Bound every field and the total candidate list before any provider call. Keep
selection validation restricted to the exact prompted candidate identities.

## Dependencies

AR-11 owns quantitative routing gates and AR-82 removes the unit-level recall
ceiling before semantic reranking.

## Acceptance

- [x] Semantic candidates include all approved routing metadata fields.
- [x] Field and total prompt sizes remain deterministically bounded.
- [x] Raw prompt bodies are never included in the judge request.
- [x] Existing provider and candidate-validation contracts remain compatible.
- [x] Full routing, performance, and merged-install gates pass.
