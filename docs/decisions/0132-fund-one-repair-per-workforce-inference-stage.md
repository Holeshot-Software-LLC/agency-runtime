---
title: "Fund one repair per workforce inference stage"
status: accepted
category: decisions
created: 2026-08-01
updated: 2026-08-01
tags: [routing, workforce, inference, configuration, budgets]
related:
  - docs/roadmap/issue-AR-218-fund-one-repair-per-inference-stage.md
  - docs/roadmap/issue-AR-201-fund-default-workforce-repair.md
  - docs/roadmap/issue-AR-203-prove-product-canary-write-and-activation.md
  - docs/roadmap/issue-AR-204-reconcile-readme-story-contract.md
  - docs/roadmap/issue-AR-217-bind-gap-evidence-to-hiring-critics.md
  - docs/decisions/0114-fund-one-default-workforce-semantic-repair.md
  - docs/decisions/0118-require-inference-owned-staffing.md
  - docs/worklog/README.md
supersedes: [docs/decisions/0114-fund-one-default-workforce-semantic-repair.md]
superseded_by: null
id: ADR-0132
type: decision
deciders: [maintainers]
---

# ADR-0132: Fund one repair per workforce inference stage

## Context

Planner and recruiter are separate inference stages. Each accepts one initial
response and, after a structural or semantic rejection, may request exactly one
provider-authored correction. ADR-0114 gave fast mode three total calls: two
baseline calls and one repair shared by both stages.

Exact product evidence shows the shared allowance is a repair lottery. When the
planner uses it, a later invalid recruiter response cannot receive the repair
that the recruiter contract advertises. Unit tests had proved planner repair
and recruiter repair separately, but never composed the two legal corrections.

## Decision

1. Fresh fast-mode configurations receive four total workforce calls: an
   initial planner call and its one possible repair, followed by an initial
   recruiter call and its one possible repair.
2. Balanced remains four. Strict remains five, reserving its fifth call for the
   existing independent staffing critic after both inference stages converge.
3. Each stage still permits at most one repair. Unused capacity is not a reason
   to retry a second rejection, select deterministically, or invent a response.
4. Bundled YAML, the typed dataclass, raw loader fallback, partial-document
   validation, timeout derivation, and decision-conformance mutation agree on
   the fresh default.
5. Persisted explicit values remain authoritative. Agency does not silently
   enlarge an operator's intentional cost or latency cap.
6. When a legacy partial document omits fast but explicitly caps balanced below
   the fresh default, the effective omitted fast value is capped to balanced.
   The persisted document stays unchanged.

## Consequences

- Both existing bounded repair contracts are reachable in the same fast-mode
  route.
- Worst-case fast-mode inference latency and generated host-hook timeout grow by
  one configured provider timeout.
- Fast and balanced share the same call ceiling; their other policy differences
  remain unchanged.
- A previously valid partial balanced-only budget remains loadable across the
  default bump without being rewritten or silently enlarged.
- Invalid second responses still fail loudly, and deterministic code still has
  no online staffing authority.

## Alternatives

- **Keep one shared repair.** Rejected because whichever stage fails second can
  lose its advertised correction solely due to call order.
- **Let a repair exceed the configured cap.** Rejected because the published
  budget must remain an enforceable upper bound.
- **Skip planner validation to save a call.** Rejected because an invalid work
  graph cannot safely govern staffing or delegation.
- **Fill an invalid recruiter response deterministically.** Rejected because
  configured online specialist selection is inference-owned.
