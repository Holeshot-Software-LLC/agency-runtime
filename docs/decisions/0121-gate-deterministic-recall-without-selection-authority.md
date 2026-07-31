---
title: "Gate deterministic recall without selection authority"
status: accepted
category: decisions
created: 2026-07-30
updated: 2026-07-30
tags: [routing, evaluation, inference, recall, safety]
related:
  - docs/roadmap/issue-AR-204-reconcile-readme-story-contract.md
  - docs/roadmap/issue-AR-205-make-default-manager-inference-safe.md
  - docs/roadmap/issue-AR-11-routing-evaluation-and-performance.md
  - docs/decisions/0030-versioned-quantitative-evaluation-gates.md
  - docs/decisions/0118-require-inference-owned-staffing.md
  - README.md
  - docs/RELEASE_CHECKLIST.md
  - docs/worklog/README.md
supersedes:
  - docs/decisions/0030-versioned-quantitative-evaluation-gates.md
superseded_by: null
id: ADR-0121
type: decision
deciders: [maintainers]
---

# ADR-0121: Gate deterministic recall without selection authority

## Context

ADR-0118 made valid inference the sole authority for substantive specialist
staffing. The v1.3 routing evaluation still called the complete route with no
provider and treated its output as selected specialists. Once deterministic
selection was correctly removed, that evaluation returned empty semantic
selections and failed every selection metric. Worse, the merge layer could
repopulate the terminal inference failure with policy companions, making a
deterministic identity look selected even though inference had failed.

Offline deterministic checks remain valuable for proving that inference sees a
bounded, relevant candidate set, that hard negatives and abstentions behave,
that policy actions and delegation are classified correctly, and that the hot
path stays within its performance budget. They cannot prove which specialist a
model would select.

## Decision

Version 1.4 of `agency eval routing` evaluates deterministic candidate recall,
not specialist selection. It uses the same affirmative-intent masking,
lexical narrowing, metadata embedding, and hard-negative candidate-union path
used by production before inference. Candidate identities in this report are
shortlist evidence only and carry the explicit contract
`deterministic_candidate_recall_only`.

The v1.4 candidate gates are:

- candidate precision at 3 of at least 0.60;
- required-candidate recall at 3 of at least 0.97;
- required-candidate case recall at 3 of at least 0.95;
- candidate top-1 relevance of at least 0.90;
- forbidden-candidate rate of zero; and
- candidate abstention accuracy of 1.0.

The versioned policy, delegation, retrieval-scale, CLI-startup, and performance
gates continue. The full-pipeline cache benchmark seeds an explicitly labelled
synthetic inference receipt under the exact production cache key; that fixture
measures cache validation and request finalization and is not selection proof.

When inference is unavailable or invalid, the complete route preserves the
terminal failure and exposes no selected, semantic, companion, or fallback
specialist identity. Deterministic policy may retain action classification for
diagnosis, but it may not turn that classification into a recommendation.

Provider-backed workforce evaluations and exact live product trials own
specialist-selection, delegation, hiring, and outcome evidence. The offline
routing report must never be cited as proof of those activities.

## Consequences

- The offline gate remains deterministic and network-free without silently
  rebuilding an offline staffing system.
- Recall regressions remain measurable against a versioned corpus while model
  selection quality is kept at the evidence boundary that can actually prove
  it.
- A terminal inference failure cannot be made cosmetically healthy by policy
  companions or resident-manager fallbacks.
- Consumers of v1.3 metric names must adopt the v1.4 candidate-recall names and
  authority marker.

## Alternatives

- **Keep calling empty output a failed selection.** Rejected because the
  no-provider route is required to select nobody.
- **Restore deterministic fallback teams for the evaluator.** Rejected because
  a test fixture must not weaken the production authority model.
- **Remove the offline routing gate entirely.** Rejected because candidate
  recall, hard negatives, policy classification, delegation, and performance
  remain load-bearing deterministic behavior.
- **Call shortlist candidates recommendations.** Rejected because retrieval
  relevance is not an inference-owned staffing decision.
