---
title: "Bind a unit's mandatory capabilities to its own artifact shape"
status: accepted
category: decisions
created: 2026-09-11
updated: 2026-09-11
tags: [workforce, planner, staffing-verifier, receipts, inference]
related:
  - docs/roadmap/issue-AR-439-planner-method-capabilities-force-incoherent-coverage.md
  - docs/decisions/0251-cap-ordinary-asks-at-two-planned-units.md
  - docs/decisions/0198-waive-the-typed-requirements-the-roster-declares-but-cannot-serve.md
  - docs/decisions/0246-make-a-wrong-neighbour-veto-name-its-neighbour.md
  - docs/decisions/0118-require-inference-owned-staffing.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
id: ADR-0252
type: decision
deciders: [owner]
---

# ADR-0252: Bind a unit's mandatory capabilities to its own artifact shape

## Status

**Accepted 2026-09-11.** Owner direction: strict staffing must work and no
fallback may hide a failure; a specialist is picked from the pool the plan
describes, and a plan must not describe a pool that contradicts itself.

## Context

Every recruiter rejection recorded as `staff_without_safe_team` since
2026-09-08 (17 unit rows: 3 on turns that later staffed, 14 on failed turns,
of which 4 on the one turn that died of that code, 9 on turns the critic,
confidence or reviewer-independence gates then ended, and 1 on a turn that
ended as `inference_invalid`) is on the capability axis. The compact intent planner names up to three
`capability_ids` per unit and the verifier turned each into a mandatory
`capability:<id>` typed requirement. Coverage of a shape-defined capability
is proven by `_CAPABILITY_RULES`, which read what a card is: `implementation`
is modify authority or an implementation lifecycle, `analysis` is advise,
plan or review authority, `planning` is plan authority or a planning
lifecycle. So a method the planner names from another shape, `implementation`
on a read-only review-report or `analysis` on a modify-authority test-code
unit, forces a specialist of that other shape onto the team. The recruiter
leaves that card out, as it should, and the deterministic gate rejects a
correct team as `retrieved_coverer_not_selected`. The compiler already holds
six ad-hoc drops for individual tokens, each added after one such failure.
Neither receipt names the requirement that forced the team, and nothing
records which capabilities were never forced.

A first draft dropped such capabilities in the compiler by probing whether a
card of exactly the unit's shape could support them. The adversarial review
falsified the premise against the live roster: 45 artifact-and-capability
pairs have same-shape cards that declare the capability (four plan-shaped
orchestrators declare `coordination`), and dropping a token also narrows the
eligible pool through `_covers_required_capability`, which "nothing else
moves" denied. The decision below keeps the token and changes only what it
mandates.

## Decision

1. **The unit keeps every planner-named capability.** The compiler does not
   drop a capability for its shape; `required_capabilities` still feeds
   recall, the recruiter prompt, the strict critic and the eligibility
   widening exactly as before, so no card loses eligibility and no query term
   disappears.
2. **Only three kinds of capability are typed coverage.**
   `mandatory_capabilities` returns the artifact-owned capability, every
   capability outside the shape-defined vocabulary (`threat-modeling`,
   `simulation` and the like, proven from a card's own declaration or a
   token match over its audited vocabulary), and a declared
   `novel_capability`, which names work the roster lacks and still reaches
   hiring as a gap. The shape vocabulary is exactly
   what `_supports_planning_capability` decides from a card's typed fields:
   the twelve authority-and-lifecycle rules plus the `architecture` and
   `risk-analysis` readings. The first live measurement after the merge
   showed why `risk-analysis` belongs there: a review unit that named it was
   rejected on the capability axis because its authority-and-token rule
   admitted a risk specialist but not the reviewer the recruiter chose. `_requirements` derives its
   `capability:` tokens from that set. A shape-defined capability named
   beside the owned one (`advisory_capabilities`) is a preference the
   recruiter weighs and the critic judges; the verifier never forces a card
   of another shape onto the team to cover it.
3. **An advisory capability is recorded, not silent.** The applied planner
   attempt carries every unit's advisory ids in the wire form
   `workforce plan advisory capabilities: unit=cap~cap`, projected on both
   durable receipts as the closed row `{unit_id, reason_code:
   plan_capability_advisory, advisory_capability_ids}`; a malformed row
   projects the attempt blank rather than partially, as ADR-0246 does for
   critic pointers. A cached plan spends no attempt and records nothing new.
4. **Nothing else moves.** The existing per-token compiler drops stay as
   explicit pins. Artifact, lifecycle, stack and authority coverage,
   eligibility, the recruiter prompt, the critic and the validators are
   unchanged. The ADR-0198 waiver mechanism is unchanged and its input set
   only narrows: a shape capability can no longer become a waived token or a
   roster-wide hiring gap, which today's roster never produced (every shape
   capability has at least four declarers). The planner
   prompt says which capabilities are mandatory coverage.

## Consequences

- The typed gate can no longer demand a modify-authority card on a read-only
  unit or a planner on a discovery unit; the pool a unit staffs from is the
  pool of its own shape, and the specialist within it is inference's choice,
  which the strict critic still judges and can veto with a named pointer.
- A plan unit that names `coordination` no longer forces one of the four
  orchestrators; they stay eligible and retrievable, and a recruiter that
  passes them over answers to the critic rather than to the gate.
- `risk-analysis` was first left outside the shape vocabulary as a
  specialty; the review noted that no modify-authority card supports it and
  the post-merge measurement caught it forcing a review unit, so it is now a
  shape capability and advisory beside the owned one.
- The advisory rows are recorded only on turns that spend a planner call, so
  a measurement over cached plans undercounts them.
- The 17 historical rows stay unexplained on the capability id; the new rows
  answer that question for every turn after this lands.
