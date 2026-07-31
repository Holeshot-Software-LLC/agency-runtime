---
title: "Require inference-owned specialist staffing"
status: accepted
category: decisions
created: 2026-07-30
updated: 2026-07-30
tags: [routing, inference, workforce, safety, failure]
related:
  - docs/roadmap/issue-AR-204-reconcile-readme-story-contract.md
  - docs/roadmap/issue-AR-205-make-default-manager-inference-safe.md
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-180-prove-codex-specialist-activation-canary.md
  - docs/decisions/0067-require-configured-inference-for-selection.md
  - docs/decisions/0087-inference-decides-from-a-relevance-shortlist.md
  - README.md
supersedes:
  - docs/decisions/0088-deterministic-typed-recall-offline-floor.md
superseded_by: null
id: ADR-0118
type: decision
deciders: [maintainers]
---

# ADR-0118: Require inference-owned specialist staffing

## Context

ADR-0088 added deterministic typed staffing as an offline convenience after
ADR-0067 had already required inference whenever configured. That compromise
made the README easier to demo without a provider, but it permits code that
cannot understand intent to recommend specialists for substantive work. It also
encouraged deterministic role anchors and fallback policies to drift back into
ordinary routing, obscuring whether a model actually chose the team.

For a system that advertises inference-selected specialists and may act on
sensitive work, a visibly labeled unsafe suggestion is still an unsafe
suggestion.

## Decision

Every substantive turn that requires specialist selection must receive and
validate an inference-owned planning and staffing decision. If no provider is
configured, every configured provider fails, or no valid response survives the
bounded repair contract, Agency fails the selection loudly and selects,
recommends, activates, delegates, and hires no specialist.

Deterministic code remains responsible for state-aware classification, bounded
candidate recall, hard host/tool/platform/authority eligibility, conflict and
coverage validation, budgets, evidence correlation, and rejection of invalid
model output. It may not create a specialist plan, promote a role anchor,
replace or reorder an inference ranking, reinterpret an invalid decision as a
gap, or choose a contractor.

Resident managers remain available to explain the failure and recovery action,
but they do not become a deterministic specialist fallback. Trivial
conversation and exact runtime-control commands that do not require staffing
remain outside this requirement.

CLI, dashboard, hooks, headers, and structured receipts expose one explicit
`inference_unavailable` or `inference_invalid` failure. They never stamp a
deterministic recruitment source for a substantive selection.

## Consequences

- Specialist and contractor suggestions always have a recorded inference
  decision or do not exist.
- Agency no longer claims an offline staffing mode; first-run guidance must
  configure a provider before substantive routing.
- Deterministic recall remains a safe, testable shortlist and verifier rather
  than a hidden decision engine.
- Provider outages are loud product failures instead of algorithm changes.

## Alternatives

- **Keep the labeled deterministic floor.** Rejected because labeling does not
  make an intent-blind recommendation safe.
- **Allow deterministic selection only for high lexical confidence.** Rejected
  because lexical confidence is not semantic understanding.
- **Let resident managers select from memory.** Rejected because that recreates
  an unrecorded model or deterministic decision outside the governed inference
  path.
