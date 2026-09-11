---
title: "AR-439: Planner method capabilities force incoherent team coverage"
status: open
category: roadmap
created: 2026-09-11
updated: 2026-09-11
tags: [workforce, planner, recruiter, staffing-verifier, reliability]
related:
  - docs/decisions/0252-bind-mandatory-capabilities-to-the-unit-shape.md
  - docs/roadmap/issue-AR-438-cap-ordinary-asks-at-two-units.md
  - docs/roadmap/issue-AR-394-recruiter-teams-fail-or-mis-select.md
  - docs/roadmap/issue-AR-384-staff-decisions-die-on-uncoverable-typed-requirements.md
  - docs/decisions/0198-waive-the-typed-requirements-the-roster-declares-but-cannot-serve.md
  - docs/decisions/0246-make-a-wrong-neighbour-veto-name-its-neighbour.md
supersedes: []
superseded_by: null
type: issue
epic: reliability
issue_id: AR-439
priority: p1
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/875
depends_on: []
blocks: []
---

# AR-439: Planner method capabilities force incoherent team coverage

## Problem

After AR-438 the recruiter's remaining rejection on ordinary asks is
`staff_without_safe_team` on the capability axis. Every one of the 17 unit
rows recorded since 2026-09-08 names `requirement_axis: capability`; 13
carry the shortfall `retrieved_coverer_not_selected` and 4
`no_eligible_coverer_in_roster`. Three sit on turns that staffed after the
rejection spent a repair; 14 sit on seven failed turns, four of them on the
one turn that died of `no_safe_sufficient_team` and the rest on turns the
critic, the confidence gate or the reviewer-independence rule ended after
the rejections had consumed the budget, and one on a turn that ended as
`inference_invalid`. In each the recruiter ranked the
faithful specialists for the unit (a lone `code-reviewer` for a review unit,
`software-test-engineer` first for a test unit, `codebase-onboarding-engineer`
first for a repository analysis) and the verifier refused the team because
one planner-named capability was left uncovered, although a card covering it
had been shown.

The cause is the requirement, not the recruiter. The compact intent planner
may name up to three `capability_ids` per unit; `compile_intent_plan`
prepends the artifact-owned capability and `_requirements` turns every id
into a mandatory `capability:<id>` typed requirement, proven by the
`_CAPABILITY_RULES` reading of a card's authority and lifecycle. Those rules
bind capabilities to what a card is: `implementation` is modify authority or
an implementation lifecycle, `analysis` is advise, plan or review authority,
`planning` is plan authority or a planning lifecycle. When the planner names
a method that belongs to another shape, such as `implementation` on a
read-only review-report or `analysis` on a modify-authority test-code unit,
the requirement forces a specialist of that other shape onto the team, the
recruiter rightly leaves it out, and the deterministic gate rejects a correct
team. The captured plans of 2026-09-10 show the pattern on every unit:
`coordination` beside `implementation` on a merge, `operations` beside
`testing` on a push check, `verification` on every review.

Roster support makes the forcing sharp. Of 293 enabled contracts,
`coordination` is supported by 4 (all by declaration; no card carries that
lifecycle today, though a resident manager would), `threat-modeling` by 4,
`operations` by 14, `documentation` by 15, while `analysis` is supported by
248 and `investigation` by 285. The compiler already carries six ad-hoc drops
for this (generic capabilities on implementation-change, `documentation` on
a plan, `data-analysis` on an analysis, ungrounded `automation`,
`communication` and `investigation`), each added after one observed failure.

Two records are missing beside the rule. The failure row names the axis and
the shortfall but never the requirement id left uncovered, so the 17 live
rows cannot say which capability forced the team. And no receipt names the
capabilities the runtime chose not to force, so that choice is invisible
after the fact.

## Current state

Repaired on branch `claude/ar439-capability-coherence-20260911` per ADR-0252.
The first draft dropped such capabilities in the compiler behind a probe of
the unit's own shape; the adversarial review falsified the probe's premise
against the live roster (45 artifact-and-capability pairs have same-shape
cards declaring the capability) and showed the drop narrowed the eligible
pool, so the repair moved to the verifier. `mandatory_capabilities` in
`staffing_verifier` keeps the artifact-owned capability, every specialty
outside the shape-defined vocabulary and a declared novelty as typed
coverage; `_requirements` derives its `capability:` tokens from that set and
`advisory_capabilities` names the rest. The unit itself, recall, eligibility,
the recruiter prompt and the critic are unchanged. The planner stage writes
each unit's advisory ids on the applied planner attempt as
`workforce plan advisory capabilities: unit=cap~cap`, and
`receipt_projection` projects them as the closed row
`{unit_id, reason_code: plan_capability_advisory, advisory_capability_ids}`
on both durable receipts, refusing a malformed detail whole; the id charset
admits the ontology's 128-character identifiers. The planner prompt says
which capabilities are mandatory coverage. Regressions cover the split on
the observed shapes, specialties and novelties, the verifier's requirement
set, a lone reviewer now covering a review that named `implementation`, an
undeclared specialty still surfacing as a hiring gap, the compiler's older
drops, the end-to-end attempt detail and receipt rows, malformed wire forms
and the row's closed keys.

Follow-ups the review named, not changed here: a specialty on a unit whose
authority no declarer carries (`risk-analysis` on a modify unit, supported by
none of 95 modify-authority cards) is still mandatory and still starves under
the ADR-0198 waiver rules; advisory rows are recorded only when a planner
call is spent, so a measurement over cached plans undercounts them; the
preflight-failure receipt's node budget leaves seven fully populated
rejected attempts of headroom beside a 16-row advisory detail. The recruiter
prompt still shows the unit's full `required_capabilities` beside a typed
requirement set that omits the advisory ones; no instruction asks it to
cover the former, but a sentence saying so would remove the ambiguity.

## Approach

Bind a unit's mandatory capabilities to its own artifact shape (ADR-0252)
in the verifier, not the compiler: keep every planner-named capability on
the unit for recall and eligibility, make only the artifact-owned capability,
specialties outside the shape vocabulary and declared novelties typed
coverage, and record the advisory ids on the applied planner attempt as a
closed receipt row. Leave the recruiter, eligibility, the critic and the
validators as they are; no fallback and no drop.

## Dependencies

AR-394 supplies the shortfall vocabulary the measurement reads. AR-438
supplies the two-unit population this must staff. ADR-0198 keeps waiving what
the roster cannot serve at all; this issue is about what the roster can serve
only with the wrong specialist.

## Acceptance

- [ ] A shape-defined capability the planner names beside the artifact-owned
      one is no typed coverage requirement, while the owned capability, a
      specialty outside the shape vocabulary and a declared novel capability
      are; the unit keeps every planner-named capability; the observed shapes
      (`implementation` on a review-report, `analysis` on a test-code unit,
      `coordination` on an implementation change, `planning` on an analysis)
      are pinned, a lone reviewer covers a review that named
      `implementation`, an undeclared specialty still surfaces as a hiring
      gap, and the existing compiler drops still hold.
- [ ] Every advisory capability reaches both durable receipts as a closed row
      on the applied planner attempt, and a malformed row projects blank
      rather than partially; the focused, named fast and decision-conformance
      checks pass.
- [ ] One fresh native run per host on the ordinary-review wording after the
      reinstall staffs with no `staff_without_safe_team` row on the capability
      axis, with the advisory rows recorded against the 17-row population.
