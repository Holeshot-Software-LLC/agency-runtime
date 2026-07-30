---
title: "Aggregate bounded recruiter repair failures"
status: accepted
category: decisions
created: 2026-07-30
updated: 2026-07-30
tags: [routing, workforce, inference, recruiter, repair, evidence]
related:
  - docs/roadmap/issue-AR-202-make-recruiter-repair-converge.md
  - docs/decisions/0088-deterministic-typed-recall-offline-floor.md
  - docs/decisions/0114-fund-one-default-workforce-semantic-repair.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
id: ADR-0115
type: decision
deciders: [maintainers]
---

# ADR-0115: Aggregate bounded recruiter repair failures

## Context

Configured online selection is inference-owned, but deterministic policy must
reject invalid recruiter output. The runtime funds one bounded recruiter repair
in fast mode. Validation previously stopped at the first invalid planned unit,
so a nine-unit response could spend that final call correcting one row only to
expose another invalid row after the budget was exhausted.

The same-provider accumulator already had enough trusted context to retain
valid rows, but its feedback did not carry the complete bounded failure set.
Persisting raw provider responses or unknown candidate identifiers would make
the diagnostic boundary unsafe.

## Decision

Recruiter semantic validation traverses every planned unit and returns one
ordered, duplicate-free failure set. Each entry contains only a governed plan
unit ID and an allowlisted invariant code. Provider-authored explanation text,
raw response fragments, and unknown candidate identifiers never enter the
exception, receipt, or repair prompt.

Within one provider's initial response and repair, the accumulator retains rows
that passed transport and semantic validation, removes failed rows, and accepts
a partial repair containing the listed failed units. It reconstructs the final
proposal in exact plan order. Accumulated rows reset before a different provider
is attempted.

Deterministic code may validate, reject, merge, and verify the inferred rows. It
does not add, promote, or reorder an online candidate. The final safe-team
verification remains authoritative and can return another bounded failure set.

## Consequences

- One repair can address every discovered invalid unit instead of chasing one
  error at a time.
- Repair prompts are smaller because already valid rows need not be repeated.
- Validation evidence remains content-free and bounded by the planned-unit
  limit.
- A repair that omits a listed failed unit, introduces a new invalid row, or
  cannot form a safe team still fails closed when the call budget is exhausted.
- The decision-conformance gate must kill first-error-only behavior with the
  production-shaped nine-unit regression.

## Alternatives

- **Increase the call budget until errors converge.** Rejected because latency
  and cost would grow with provider mistakes and the published cap would lose
  meaning.
- **Ask the model to repeat every row.** Rejected because it wastes tokens and
  can corrupt rows that already passed validation.
- **Choose or repair candidates deterministically.** Rejected because it would
  silently replace inference-owned online selection.
- **Persist the raw invalid response for debugging.** Rejected because
  provider-authored content and unknown identifiers are outside the durable
  diagnostic boundary.
