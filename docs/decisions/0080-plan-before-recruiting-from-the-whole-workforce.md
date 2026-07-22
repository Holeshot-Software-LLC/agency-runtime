---
title: "Plan before recruiting from the whole workforce"
status: accepted
category: decisions
created: 2026-07-21
updated: 2026-07-21
tags: [routing, planning, recruitment, inference]
related:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-120-normalized-workforce-recruitment-index.md
  - docs/roadmap/issue-AR-121-inference-planning-and-staffing.md
supersedes: []
superseded_by: null
id: ADR-0080
type: decision
deciders: [maintainers]
---

# ADR-0080: Plan before recruiting from the whole workforce

## Context

Directly matching an ask to agent descriptions encourages keyword collisions,
premature assurance roles, and shortlist blind spots. The workforce is broad
enough that selection must first understand the work and decisive qualifiers.

## Decision

Configured inference first produces bounded typed work units without agent
names. A separate recruiter evaluates the complete compact workforce index and
detailed shortlist cards. Deterministic code remains the staffing authority and
rejects incomplete, forbidden, incompatible, disabled, ineligible, or
low-margin selections. Fast and strict modes may combine or add inference calls
without changing those schemas and invariants.

## Consequences

Selection gains semantic understanding and whole-roster reach while remaining
auditable and safe. It adds versioned schemas, index caching, provider cost, and
new evaluation obligations. Without configured inference, the degraded path
cannot invent workers and must abstain when deterministic evidence is weak.

## Alternatives

Keyword routing was rejected because plausible overlap is not capability
coverage. Retrieval-only shortlists were rejected because they can hide the
best worker. Letting inference directly activate agents was rejected because
confidence does not enforce eligibility or composition.
