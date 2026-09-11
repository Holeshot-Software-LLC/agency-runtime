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

Every terminal `staff_without_safe_team` since 2026-09-08 (17 unit rows) is
on the capability axis. The compact intent planner names up to three
`capability_ids` per unit and the compiler turns each into a mandatory
`capability:<id>` typed requirement. The verifier proves coverage through
`_CAPABILITY_RULES`, which read a card's authority and lifecycle:
`implementation` is modify authority or an implementation lifecycle,
`analysis` is advise, plan or review authority, `planning` is plan authority
or a planning lifecycle, `coordination` is a lifecycle phase no card
declares. So a method the planner names from another shape, `implementation`
on a read-only review-report or `analysis` on a modify-authority test-code
unit, can only be covered by a specialist of the wrong kind. The recruiter
leaves that card out, as it should, and the deterministic gate rejects a
correct team as `retrieved_coverer_not_selected`. The compiler already holds
six ad-hoc drops for individual tokens, each added after one such failure.
Neither receipt names the requirement that forced the team, and nothing
records what the compiler dropped.

## Decision

1. **Shape coherence decides what is mandatory.** A planner-named capability
   is kept on a unit only when the ontology's own support rule can be met by a
   card whose typed shape is the unit's: its artifact kind, its lifecycle
   phase, an authority that satisfies the unit's authority under the
   verifier's compatibility table, and its domains. The compiler evaluates
   `_supports_planning_capability` against that shape probe. The
   artifact-owned capability is always coherent by construction.
2. **Specialist and novel capabilities stay mandatory.** A capability with no
   broad rule (`threat-modeling`, `simulation`, `translation` and the like)
   names a specialty any shape may carry through `capability_ids`, and a
   declared `novel_capability` names work the roster lacks; both keep their
   typed requirement so the coverage-gap and hiring path is unchanged.
3. **A drop is recorded, not silent.** The applied planner attempt carries
   every dropped id in the wire form
   `workforce plan capability demotions: unit=cap~cap`, projected on both
   durable receipts as a closed row `{unit_id, reason_code:
   plan_capability_demoted, demoted_capability_ids}`; a malformed row
   projects the attempt blank rather than partially, as ADR-0246 does for
   critic pointers.
4. **Nothing else moves.** The existing per-token compiler drops stay as
   explicit pins. The recruiter prompt, the verifier's coverage and
   eligibility, the critic and the validators are unchanged; the recruiter
   still sees only the capabilities the unit keeps.

## Consequences

- The typed gate can no longer demand a modify-authority card on a read-only
  unit or a planner on a discovery unit, which removes the observed cause of
  every capability-axis rejection without weakening any coverage a card of
  the unit's own shape could provide.
- Recall loses the dropped tokens as query terms; a unit that needed the
  specialist those tokens retrieved should have named the specialty (a
  rule-less capability) or its domain instead, and the planner prompt says
  so.
- A planner that keeps naming incoherent methods costs nothing at staffing
  time but leaves demotion rows, so the habit is measurable per host.
- The 17 historical rows stay unexplained on the capability id; the new rows
  answer that question for every turn after this lands.
