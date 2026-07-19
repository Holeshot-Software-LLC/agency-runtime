---
title: "Bound native delegation correction to one evidence-checked pass"
status: accepted
category: decisions
created: 2026-07-18
updated: 2026-07-18
tags: [delegation, stop, retries, evidence, native-hosts]
related:
  - docs/roadmap/issue-AR-87-bounded-native-delegation-plans.md
  - docs/roadmap/issue-AR-27-authoritative-delegation-stop-enforcement.md
  - docs/roadmap/issue-AR-58-unit-aware-delegation-assignment.md
  - docs/decisions/0011-explicit-delegation-evidence-lifecycle.md
  - docs/decisions/0045-turn-scoped-specialist-activation.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
id: ADR-0071
type: decision
deciders: [maintainers]
---

# ADR-0071: Bound native delegation correction to one evidence-checked pass

## Context

Agency should keep the parent responsive by recommending native delegation for
substantial independent work, but a suggestion alone cannot prove execution.
Unbounded Stop feedback can trap a host in a terminal-correlation loop, while no
feedback lets a parent silently ignore a high-value isolation boundary.

## Decision

Express delegation guidance per work unit as `optional`, `preferred`, or
`strongly_preferred`; default operator mode is `prefer`. Include the exact goal,
deliverable, specialists, rationale, confidence, dependencies, parallel hints,
mutation and resource scope, required tools, and required evidence in a bounded
durable plan.

For `preferred`, let the parent proceed directly only with a durable reason. For
`strongly_preferred`, if current-turn evidence contains neither an authoritative
native spawn nor an explicit decline, Stop may atomically claim one corrective
pass. The correction names the exact units, specialists, native mechanism, and
benefit. It remains part of the same external turn and never opens a new trace.

On the next Stop, revalidate the complete evidence. If delegation still did not
occur, terminate normally with a durable `delegation_declined` or
`retry_exhausted` outcome and bounded reason. Never request a third pass, reopen
a terminal trace, treat Stop feedback as user input, or claim execution from a
recommendation. The native host may refine, merge, add, or decline units; Agency
never replaces its scheduler.

## Consequences

- Strong delegation guidance has one meaningful enforcement opportunity.
- A host cannot enter an infinite Stop/correlation loop.
- Declining delegation remains valid and observable rather than fabricated
  execution.
- The parent remains free to do focused work directly.
- Retry state and finalization must be atomic and turn-scoped.

## Alternatives

- Require delegation for every selected specialist. Rejected because focused
  work does not justify worker overhead.
- Repeat Stop correction until a worker appears. Rejected because it creates
  loops and can never manufacture native execution evidence.
- Never challenge ignored delegation. Rejected because the parent would remain
  blocked on work explicitly judged to benefit from isolation or parallelism.
