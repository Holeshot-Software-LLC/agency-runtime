---
title: "Run child-specific Agency activation through native host lifecycles"
status: accepted
category: decisions
created: 2026-07-18
updated: 2026-07-18
tags: [delegation, children, hosts, activation, correlation]
related:
  - docs/roadmap/issue-AR-25-turn-scoped-specialist-evidence.md
  - docs/roadmap/issue-AR-58-unit-aware-delegation-assignment.md
  - docs/roadmap/issue-AR-82-full-roster-unit-routing.md
  - docs/decisions/0045-turn-scoped-specialist-activation.md
  - docs/decisions/0068-select-compatible-specialist-closures-per-unit.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
id: ADR-0070
type: decision
deciders: [maintainers]
---

# ADR-0070: Run child-specific Agency activation through native host lifecycles

## Context

Native planners can create children independently of an Agency recommendation,
and a parent's selected specialists may not fit a child's exact delegated unit.
Copying parent prompt context into every child inflates context, creates
authority conflicts, and makes delegation evidence impossible to reconcile.

## Decision

Every native child runs one bounded Agency preflight against its exact task.
The child receives only its task, required repository/runtime policy, selected
specialist contract and prompt, acceptance and evidence requirements, and
correlation identifiers. It never inherits every parent specialist or the
resident managers as ordinary prompts.

Use the host's native lifecycle:

- Claude Code uses Agent/PreToolUse and SubagentStart/Stop integration.
- OpenClaw uses its plugin and subagent hooks while preserving Task Flow,
  recovery, and announce semantics.
- Codex uses native collaboration workers, stable work-unit labels, and a
  bounded activation recipe.
- Hermes uses official worker lifecycle hooks where available.

One-use activation grants bind parent session, parent trace, work-unit ID,
specialist slug, version, prompt hash, child host, and expiry. Record
recommended specialist, actual loaded specialist, native worker identity,
native run identity, requested model, authoritative actual provider/model,
LiteLLM router identity, outcome, and evidence separately. A recommendation is
not delegation, and delegation is not proven without both worker and run
identity.

## Consequences

- Native children get expertise tailored to their actual assignment.
- Parent prompts do not accumulate in child contexts.
- Children created by native planners still participate in Agency selection.
- Host scheduling and recovery remain native responsibilities.
- Hosts without a live installed lifecycle remain contract-tested rather than
  falsely reported as live-supported.

## Alternatives

- Copy all parent specialists into every child. Rejected because task scope and
  authority differ per worker.
- Require Agency to create every child. Rejected because it would replace the
  native planner.
- Infer delegation from a recommendation or tool name. Rejected because
  execution requires authoritative native identities.
