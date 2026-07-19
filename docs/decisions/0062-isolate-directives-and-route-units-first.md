---
title: "Isolate directive specialists and route each work unit before hydration"
status: superseded
category: decisions
created: 2026-07-17
updated: 2026-07-18
tags: [routing, delegation, prompts, isolation, replay]
related:
  - docs/roadmap/issue-AR-81-conflict-safe-direct-context.md
  - docs/roadmap/issue-AR-82-full-roster-unit-routing.md
  - docs/roadmap/issue-AR-84-bounded-semantic-agent-cards.md
  - docs/decisions/0045-turn-scoped-specialist-activation.md
  - docs/decisions/0054-unit-aware-assignment-and-event-driven-dag.md
  - docs/worklog/README.md
supersedes: []
superseded_by: docs/decisions/0069-enforce-conflicts-before-prompt-composition.md
id: ADR-0062
type: decision
deciders: [maintainers]
---

# ADR-0062: Isolate directive specialists and route each work unit before hydration

## Context

Selecting a small global specialist set before examining individual work units
creates a recall ceiling: an omitted specialist cannot win any unit. Hydrating
multiple full prompts into one direct host context creates a separate authority
problem because implementers, reviewers, and coordinators can issue competing
instructions without an isolation boundary.

## Decision

Treat each worker context as a single-directive authority boundary. Route every
bounded delegated work unit independently against the full revision-stable
active catalog, persist its exact content-free winner for deterministic replay,
and hydrate winners only after assignment. Isolated hosts may prepare separate
native specialist activations. Direct hosts hydrate one directive specialist by
default; the governed `agents-orchestrator` and `chief-of-staff` no-match pair is
the only current multi-prompt exception because it is defined and tested as one
fallback coordination unit. Other selected roles remain bounded suggestions and
must execute in separate workers before their instructions become authoritative.

The semantic judge may receive richer approved metadata cards, but never raw
prompt bodies. Every card and provider request remains deterministically bounded.

## Consequences

- A specialist omitted by the global summary route can still win its own unit.
- Implementer and independent-reviewer directives do not silently merge.
- Replay records exact winners instead of re-running selection against a changed roster.
- Direct-only hosts sacrifice simultaneous prompt breadth for deterministic authority.
- Compatibility metadata can later permit additional co-loading without weakening the default.

## Alternatives

- Route only once globally. Rejected because top-k selection imposes a hard unit-level recall ceiling.
- Concatenate every selected prompt. Rejected because prompt order becomes an implicit and unreviewed authority policy.
- Let the semantic judge read full prompt bodies. Rejected because it expands latency, injection surface, and provider disclosure.

## Provenance

AR-81, AR-82, and AR-84 record implementation and verification; commit
provenance is added after the substantive commit exists.
