---
title: "Fund one default workforce semantic repair"
status: accepted
category: decisions
created: 2026-07-30
updated: 2026-07-30
tags: [routing, workforce, inference, configuration, budgets]
related:
  - docs/roadmap/issue-AR-200-diagnosable-decision-conformance.md
  - docs/roadmap/issue-AR-201-fund-default-workforce-repair.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
id: ADR-0114
type: decision
deciders: [maintainers]
---

# ADR-0114: Fund one default workforce semantic repair

## Context

The configured-provider path always invokes an inference planner followed by an
inference recruiter. Each stage may reject one structurally transported response
that violates deterministic semantics and ask the same provider for one bounded
correction. The fast-mode production default supplied only the two baseline
calls, making any recruiter correction unreachable after planning. Bundled and
Python defaults also disagreed at one versus two calls.

AR-200 trace `019fb31f-5da6-7dd0-a983-9b983f767b9f` demonstrated the exact
failure: planner applied, recruiter contract rejected, total budget exhausted,
and no specialist evidence was published.

## Decision

Fresh fast-mode configurations receive three total workforce calls: one planner,
one recruiter, and one shared bounded semantic repair. Balanced remains four so
both stages can repair once, and strict remains five so it can also run its
independent critic.

Every fresh-default source must agree: bundled YAML, typed dataclass, raw loader
fallback, and partial-document validation. Generated hook timeouts continue to
derive from the effective call budget.

Persisted explicit values remain authoritative, including historical one- and
two-call values. Agency cannot distinguish a previously generated value from an
intentional latency or cost cap, so updates do not migrate it silently. The
operator may deliberately raise that override when semantic repair is desired.

The curated decision-conformance gate lowers the typed default to two in a
private copy and requires the production-sequence regression to fail.

## Consequences

- Fresh installs can execute the bounded repair contract they advertise.
- Fast mode remains bounded, but its worst-case inference latency and generated
  host-hook timeout increase by one provider timeout.
- Existing explicit lower budgets retain opt-out semantics and may still
  abstain before repair until deliberately changed.
- Deterministic code still cannot invent a missing staffing decision or replace
  an invalid provider response.

## Alternatives

- **Spend a repair call outside the configured cap.** Rejected because the
  published call budget would stop being an enforceable upper bound.
- **Infer a missing staff or gap decision deterministically.** Rejected because
  configured online selection is inference-owned.
- **Rewrite every explicit one- or two-call configuration during upgrade.**
  Rejected because Agency cannot prove those values were not intentional cost
  or latency limits.
- **Leave fast mode unable to repair.** Rejected because that contradicts the
  runtime's explicit bounded semantic-repair contract and failed the ordinary
  live path.
