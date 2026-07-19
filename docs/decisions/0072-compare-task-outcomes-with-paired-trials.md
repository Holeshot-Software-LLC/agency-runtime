---
title: "Compare task outcomes with evidence-labelled paired trials"
status: accepted
category: decisions
created: 2026-07-18
updated: 2026-07-18
tags: [evaluation, outcomes, comparison, evidence, delegation]
related:
  - docs/roadmap/issue-AR-88-compare-agency-native-outcomes.md
  - docs/roadmap/issue-AR-11-routing-evaluation-and-performance.md
  - docs/decisions/0030-versioned-quantitative-evaluation-gates.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
id: ADR-0072
type: decision
deciders: [maintainers]
---

# ADR-0072: Compare task outcomes with evidence-labelled paired trials

## Context

Routing precision, recall, contract tests, and simulated delegation lifecycles
prove important mechanics but do not prove that Agency improves an actual host's
task outcome. Mixing simulated and live evidence or changing the model between
variants would support an unjustified superiority claim.

## Decision

Evaluate native-only, Agency observe, Agency prefer, and Agency strong variants
with exact scenario/trial/host pairs. Record the requested and authoritative
actual model separately from any router identity. Use blinded external quality
review where possible and measure completion, failed tests, escaped defects,
duration, cost, retries, duplicate work, merge conflicts, synthesis failures,
supervisor intervention, delegated units, and delegation regret.

Every observation declares one evidence class: `live_host`,
`installed_isolated`, `contract_only`, or `simulated`. Only model-matched paired
live-host trials can satisfy a directional-claim eligibility gate. That gate is
not itself a statistical superiority conclusion. The runtime and documentation
must never promote other evidence classes into a live claim.

Store comparison observations in a strict bounded, content-free schema by
default. Preserve scenario and run identities without prompts, secrets, direct
personal data, or payment data. Report limitations and missing baselines
explicitly.

## Consequences

- Delegation quality is evaluated by outcomes, not spawn counts.
- Simulations remain useful without being mistaken for product evidence.
- Router and actual-model mismatches invalidate controlled live pairs.
- Cost and latency regressions remain visible beside quality changes.
- Strong claims require a separate statistical and reviewer-quality analysis
  after the minimum evidence gate.

## Alternatives

- Compare only routing labels. Rejected because correct expertise selection does
  not prove execution quality.
- Treat installed isolated canaries as live production evidence. Rejected
  because isolation and capability maturity differ.
- Announce superiority whenever average quality increases. Rejected because
  sample size, pairing, defects, model consistency, and reviewer blindness also
  matter.
