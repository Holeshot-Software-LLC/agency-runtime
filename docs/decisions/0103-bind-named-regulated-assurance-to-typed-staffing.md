---
title: "Bind named regulated assurance to typed staffing requirements"
status: accepted
category: decisions
created: 2026-07-27
updated: 2026-07-27
tags: [routing, workforce, assurance, safety]
related:
  - docs/roadmap/issue-AR-179-fail-named-regulated-assurance-gaps-closed.md
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-121-inference-planning-and-staffing.md
  - docs/decisions/0080-plan-before-recruiting-from-the-whole-workforce.md
  - docs/decisions/0082-schedule-assurance-by-artifact-lifecycle.md
  - docs/decisions/0087-inference-decides-from-a-relevance-shortlist.md
supersedes: []
superseded_by: null
id: ADR-0103
type: decision
deciders: [maintainers]
---

# ADR-0103: Bind named regulated assurance to typed staffing requirements

## Context

The compact planner owns semantic organization, while local code validates
typed coverage. A live DO-178C avionics request exposed a boundary error: the
planner could omit the named standard, after which generic review contracts
covered every remaining broad requirement and the verifier accepted an unsafe
false-sufficient team.

## Decision

Treat an explicit named standard in high-assurance context as an immutable
staffing requirement. Deterministic enrichment attaches a normalized
`regulated-assurance-<standard>` capability to an independent review unit, and
plan policy rejects omission of either the review or requirement.

A worker covers that requirement only when its governed contract explicitly
does so. Semantic similarity, generic review authority, or broad testing
experience cannot substitute. If no qualified worker exists, the verifier
abstains and the normal governed-gap path may recruit a contractor. Recognition
is bounded to assurance-qualified or intrinsically regulated identifiers so an
ordinary format reference does not manufacture a gap.

## Consequences

- Named regulated scope cannot disappear between the request and staffing.
- A false-sufficient generic team becomes a visible, hireable gap.
- Qualified future employees or contractors opt in through an auditable typed
  capability instead of free-form model reasoning.
- The bounded recognizer requires maintenance as supported standard families
  expand; unknown prose-only regulation still relies on inference and review.

## Alternatives

- **Trust planner wording.** Rejected because the reproduced plan erased the
  safety-critical requirement before deterministic verification.
- **Hard-code an avionics worker.** Rejected because the defect is a general
  typed-grounding failure and no qualified worker currently exists.
- **Let a generic reviewer cover standards by semantic tokens.** Rejected
  because certification claims require explicit governed scope.
