---
title: "Enforce specialist conflicts before prompt composition"
status: accepted
category: decisions
created: 2026-07-18
updated: 2026-07-18
tags: [prompts, conflicts, authority, isolation, review]
related:
  - docs/roadmap/issue-AR-81-conflict-safe-direct-context.md
  - docs/roadmap/issue-AR-82-full-roster-unit-routing.md
  - docs/decisions/0062-isolate-directives-and-route-units-first.md
  - docs/decisions/0068-select-compatible-specialist-closures-per-unit.md
  - docs/worklog/README.md
supersedes: [docs/decisions/0062-isolate-directives-and-route-units-first.md]
superseded_by: null
id: ADR-0069
type: decision
deciders: [maintainers]
---

# ADR-0069: Enforce specialist conflicts before prompt composition

## Context

Prompt ordering is not a safe conflict-resolution mechanism. Two individually
reasonable specialists can issue contradictory mutation, approval, review, or
product directives. A global route can also put implementers and independent
reviewers into the same context, destroying separation of duties.

## Decision

Enforce conflicts at four explicit boundaries:

1. Before scoring, remove agents that cannot operate under the current host,
   platform, tools, permissions, security policy, mutation scope, or authority.
2. During compatible-set construction, solve explicit `conflicts_with`,
   `requires`, authority, context-mode, independence, likely resource overlap,
   and output-contract constraints jointly.
3. Before hydration, use one directive specialist per worker context by
   default. Co-load complete prompts only when every agent is `direct_safe`,
   authority is non-overlapping, the exact combination is permitted, and the
   deterministic combined budget passes. Implementers and independent reviewers
   always remain separate. Overlapping mutations are sequenced or placed in
   native isolated worktrees.
4. After execution, reconcile outputs using declared authority, acceptance
   criteria, evidence strength, reviewer findings, and durable decisions.
   Escalate unresolved equal-authority product choices to the user.

Resident manager contracts are a separate parent kernel, not an exception that
allows arbitrary specialist prompts to share a context. Persist rejected
compatibility edges and execution constraints without persisting full foreign
prompt bodies.

## Consequences

- Conflicts become visible graph constraints rather than prompt-order accidents.
- Independent review retains meaningful separation from implementation.
- Safe advisory combinations may still share a bounded direct context.
- File and resource contention can be scheduled before mutation begins.
- Some high-scoring combinations are rejected in favor of a smaller compatible
  set or explicit abstention.

## Alternatives

- Concatenate prompts by score. Rejected because score does not define authority.
- Let the model resolve all conflicts after hydration. Rejected because the
  conflicting instructions have already entered one authority context.
- Always serialize every specialist. Rejected because compatible independent
  work should remain parallelizable.
