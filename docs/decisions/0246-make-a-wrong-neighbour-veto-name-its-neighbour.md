---
title: "Make a wrong-neighbour veto name its neighbour, and check the name"
status: accepted
category: decisions
created: 2026-09-10
updated: 2026-09-10
tags: [workforce, critic, staffing, receipts, inference]
related:
  - docs/roadmap/issue-AR-433-name-the-neighbour-a-wrong-neighbour-veto-points-at.md
  - docs/roadmap/issue-AR-434-plan-policy-reads-a-handoff-request-as-a-code-mutation.md
  - docs/decisions/0205-show-the-critic-the-eligible-neighbourhood-it-judges-against.md
  - docs/decisions/0200-bind-the-strict-critic-to-the-advisory-doctrine.md
  - docs/decisions/0202-read-the-recruiter-reply-where-no-safety-property-lives.md
  - docs/decisions/0118-require-inference-owned-staffing.md
  - docs/roadmap/reference-workforce-inference-stages.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
id: ADR-0246
type: decision
deciders: [owner]
---

# ADR-0246: Make a wrong-neighbour veto name its neighbour, and check the name

## Status

**Accepted 2026-09-10.** Implements AR-433, the first item of the fresh-agent
reliability handoff after the owner's alternating-recruitment observation.

## Context

ADR-0205 gave the strict critic, per unit, the complete eligible neighbourhood
it judges against and told it that a wrong-neighbour veto must point at a card
in that list. The instruction lived in the prompt and the contract; the
response schema (`approved`, `reason_codes`) had nowhere to put the pointer.
The critic could satisfy the letter of the schema with the bare code, and did:
between 2026-09-08 and 2026-09-10 it vetoed 30 nontrivial turns across five
hosts, 27 of them on `wrong-neighbor-selection`, and no durable receipt could
say which card it preferred or which selected worker it would replace. Twice
it wrote a name into the code itself (AR-416), which is the only channel it
had. Whether those vetoes were right is unknowable from the records.

The owner saw this as recruitment failing every other call. The immutable
receipts of the observed session show two terminal critic vetoes on
operational requests between two staffed engineering requests; the pattern is
content and a high veto rate, not periodicity. The rate is the defect, and it
sits at a boundary where the runtime already holds both identities a
wrong-neighbour claim is about: the worker it selected on the unit and the
eligible card it did not.

## Decision

1. **The pointer is part of the contract.** `CRITIC_RESPONSE_SCHEMA` gains an
   optional `wrong_neighbors` array of at most eight closed objects, each
   naming `unit_id`, `selected_agent_id` and `neighbor_agent_id` in the
   planned-unit and roster-identity charsets. `critic_contract` states
   `wrong_neighbor_pointer_required`, `wrong_neighbor_pointer_fields` and
   `wrong_neighbor_pointer_verified_by_runtime`; the system prompt says the
   same in words and tells the critic that when it cannot name such a card the
   ground does not apply.
2. **The runtime checks the pointer against its own facts.** For any
   `wrong-neighbor-selection` code, bare or qualified, the parser requires a
   non-empty pointer array and verifies each row against the same
   `eligible_neighbourhood` document it sent: the unit is planned, the
   selected worker was selected on it, the neighbour is eligible on it, the
   neighbour is not itself selected, and the unit's selected workers are not
   its whole neighbourhood. A pointer without the code, or on an approval, is
   a shape failure. The three outcomes are closed critic validation codes:
   `critic_wrong_neighbor_unnamed`, `critic_wrong_neighbor_unverified` and
   `critic_wrong_neighbor_shape_invalid`, registered beside the existing six.
3. **A failed check is a contract failure, never a verdict.** It takes the
   existing bounded semantic repair (one re-ask carrying the failed check and
   a planned unit id, never the critic's text), and if the repair also fails
   the stage fails as `workforce_inference_failed` with the critic's
   validation code on the attempt. The turn is not staffed and not vetoed;
   the receipt says the critic could not ground its claim. The runtime
   approves nothing and selects nothing (ADR-0118).
4. **A verified pointer is retained.** It rides the applied critic attempt's
   `validation_detail` in the wire form `unit=selected>neighbor` under the
   prefix `workforce critic wrong-neighbor pointers: `, and both receipts
   project it through `project_nomination_failures` as a per-unit
   `validation_failures` row with `reason_code`
   `critic_wrong_neighbor_selection`, `selected_agent_id` and
   `neighbor_agent_id`. The row is admitted only in exactly that shape and
   re-projects to itself (ADR-0202). The staffing decision's projected codes,
   the routing receipt's global codes and the fail-open disclosure line are
   unchanged.
5. **Not changed.** The critic's independence and route, the four grounds and
   the never-veto list (ADR-0200), the neighbourhood document (ADR-0205), the
   sixteen-code and 56-character receipt-code bounds (AR-416), and every other
   ground, which still needs no pointer.

## Consequences

- A wrong-neighbour veto is now a checkable claim: the receipt names the card
  the critic preferred and the worker it would replace, so the next
  investigation can read the veto instead of capturing it.
- A critic that cannot name an eligible better card can no longer use the
  ground. The fresh diagnostic in AR-433 records how the live critic behaves
  under the new contract on the two exact vetoed requests; the decision does
  not predict the outcome.
- Fixtures that vetoed with a bare `wrong-neighbor-selection` on a snapshot
  whose selected team was its whole neighbourhood either name a pointer on a
  larger neighbourhood or use a ground that needs none. The captured
  qualified veto of AR-416 keeps its qualified code and adds the pointer that
  code always implied.
- A failed pointer check costs one extra critic call inside the existing
  strict budget, on exactly the turns that were dying anyway.

## Alternatives

- **Approve when the critic cannot name a neighbour.** Rejected: the runtime
  would be issuing a staffing verdict the critic did not give, which ADR-0118
  and AR-306 forbid; a contract failure with a named cause is the truthful
  outcome.
- **Drop `wrong-neighbor-selection` as a ground.** Rejected: ADR-0205's live
  measurement showed vetoes that named real eligible cards, which is the
  critic doing its job; the ground is kept and made accountable.
- **Carry the pointer in the reason codes.** Rejected: AR-416 already showed
  a name folded into a code overruns the 56-character projection bound and
  must be omitted; identities belong in a typed field the projection admits
  by shape.
- **Add a receipt column for the pointer.** Rejected: the preflight-failure
  receipt is an exact column set and the per-unit `validation_failures` row
  already exists for the same purpose on rejected recruiter attempts.
