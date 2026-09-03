---
title: "Bind the strict critic to the advisory doctrine and name its veto on the receipts"
status: accepted
category: decisions
created: 2026-09-03
updated: 2026-09-03
tags: [workforce, critic, staffing, receipts, inference]
related:
  - docs/roadmap/issue-AR-386-strict-critic-vetoes-verifier-accepted-install-turns.md
  - docs/roadmap/issue-AR-384-staff-decisions-die-on-uncoverable-typed-requirements.md
  - docs/roadmap/issue-AR-374-host-capability-vocabulary-gap.md
  - docs/roadmap/issue-AR-306-bind-strict-critic-semantics.md
  - docs/roadmap/issue-AR-304-preserve-recruiter-critic-validation-diagnostics.md
  - docs/roadmap/reference-workforce-inference-stages.md
  - docs/decisions/0198-waive-the-typed-requirements-the-roster-declares-but-cannot-serve.md
  - docs/decisions/0110-remove-agency-owned-windows-hello.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
id: ADR-0200
type: decision
deciders: [owner]
---

# ADR-0200: Bind the strict critic to the advisory doctrine and name its veto on the receipts

## Status

**Accepted 2026-09-03.** Implements AR-386, item 2 of the AR-383 capsule's
next package, per the approach filed in the issue.

## Context

Agency supplies specialist expertise and never executes anything; the host
applies the selected team's expertise and holds every execution authority
(ADR-0110, README "it does not execute specialists"). AR-374 established
that an install is therefore planned as a plan-authority unit, and ADR-0198
made the verifier accept such units with the typed requirements the roster
cannot serve recorded as `roster_coverage_gap` waivers.

That moved the gate to the strict critic, and the critic closed it every
time. On the four verifier-accepted install turns of 2026-09-03 it returned
`wrong-neighbor-selection` and `planner-domain-mismatch`, which are fair,
and `selected-team-lacks-live-installation-authority` and
`missing-implementation-lifecycle-assurance`, which are not: no worker can
hold live installation authority in an advisory workforce, and a plan with
no implementation unit owes no assurance of implementation work. Nothing in
the critic's contract or system prompt said any of this. AR-306 had bound
the critic to the configured thresholds and selected-only composition and
no further.

The veto itself was also unreadable afterwards. On a rejection the staffing
decision was replaced by one `staffing_critic_rejected` reason, and the
critic's codes survived only in the routing result's error string, which no
durable receipt carries. Diagnosing a veto needed the capture harness.

## Decision

1. **The critic contract states the doctrine.** `critic_contract` carries
   `workforce_is_advisory: true`, `execution_authority_holder: host`,
   `selected_authority_bound_by_eligibility: true`,
   `roster_coverage_gaps_are_runtime_waivers: true` and
   `plan_authority_units_for_host_side_work_are_intended: true`, plus two
   lists: `veto_grounds` (wrong-neighbor selection, lifecycle assurance the
   plan calls for, unsafe selected-team composition, unsupported confidence)
   and `never_veto_for` (execution or installation authority, waived roster
   coverage gaps, plan-authority units for host-side work, implementation
   units the planner did not plan, completed task evidence). The thresholds
   and the selected-only composition contract from AR-306 are unchanged.
2. **The system prompt says the same in words.** `_CRITIC_SYSTEM` states
   that Agency is advisory and the host executes, that no worker can or need
   hold live authority, that a plan- or review-authority unit for host-side
   work is the intended shape, that each selected worker's authority was
   already bound by eligibility, that `roster_coverage_gap` entries are
   roster facts, and that the critic must not demand an implementation unit
   the planner did not plan. The four grounds it may veto on are restated
   with the lifecycle ground narrowed to assurance the plan calls for.
3. **The veto is named on the receipts.** On a rejection the staffing
   decision carries `staffing_critic_rejected` followed by each critic code
   projected as `critic_<code>` with hyphens folded to underscores, at most
   sixteen, at most 56 characters each, validated against the critic's own
   code charset first. The projection satisfies the preflight-failure
   receipt's underscore vocabulary (`staffing_reason_codes`), the routing
   receipt's `global_reason_codes`, and the fail-open disclosure's
   512-character line, so all three name the veto beside the verifier's
   codes. The routing result's `abstention_codes` keep the raw codes exactly
   as before.
4. **Not changed.** The critic route, its independence requirement, the
   strict-mode gate itself, and the rule that an invalid critic reply is a
   bounded semantic repair and never durable content (AR-304). The projected
   codes are the schema-validated identifiers the critic already returns,
   the same class the hiring critic's codes have always carried into hiring
   events.

## Consequences

- Measured 2026-09-03 on the branch runtime, strict mode, the same nine
  install wordings as the AR-384 measurement plus two from AR-385, critic on
  the same deployment: six turns reached the critic; it approved two install
  turns, which completed with staffed teams of six and four specialists, and
  vetoed four, every one on `wrong-neighbor-selection` alone. Neither of the
  two doctrine-breaking codes recurred. The five turns that never reached
  the critic died on AR-384 and AR-373 residue at the recruiter or verifier.
- Every one of the four vetoes reached the durable preflight-failure receipt
  as `['staffing_critic_rejected', 'critic_wrong_neighbor_selection']`,
  where the same receipts had carried the class code alone.
- A veto is diagnosable from the durable receipts and the fail-open
  disclosure line the host shows, without the capture harness.
- The chaos harness's `critic_rejected` shape now expects the projected code
  beside the class code; the fail-open disclosure tests were unaffected.
- The critic's model-authored codes are not a closed vocabulary. They are
  bounded, charset-closed identifiers, which is the same bound under which
  the hiring critic's codes reach durable hiring events; a code that fails
  the bound is dropped, never cut or rewritten.

## Alternatives

- **Drop the critic in strict mode, or auto-approve on any code.** Rejected
  in the issue: the fair vetoes (`wrong-neighbor-selection`,
  `planner-domain-mismatch`) are exactly what strict mode exists for.
- **Filter execution-authority codes out of the verdict at runtime.**
  Rejected: it would second-guess a model verdict by string matching, and a
  critic that reasons from a contract stating the doctrine has no basis for
  the code in the first place; if it still returns one, the receipt now says
  so and the wording is the next thing to fix.
- **Carry the critic's codes in a new receipt field.** Rejected: the
  preflight-failure receipt is an exact key set stored as columns, so a new
  field means a schema version and a store migration for what the existing
  `staffing_reason_codes` list already expresses once the codes fit its
  vocabulary.
