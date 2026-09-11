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

After AR-438 the recruiter's remaining terminal failure on ordinary asks is
`staff_without_safe_team` on the capability axis. Every one of the 17 unit
rows recorded since 2026-09-08 (3 on preflight results, 14 on failure
receipts) names `requirement_axis: capability`; 13 carry the shortfall
`retrieved_coverer_not_selected` and 4 `no_eligible_coverer_in_roster`. The
recruiter ranked the faithful specialists for the unit (a lone
`code-reviewer` for a review unit, `software-test-engineer` first for a test
unit, `codebase-onboarding-engineer` first for a repository analysis) and
the verifier refused the team because one planner-named capability was left
uncovered, although a card covering it had been shown.

The cause is the compiler, not the recruiter. The compact intent planner may
name up to three `capability_ids` per unit; `compile_intent_plan` prepends
the artifact-owned capability and `_requirements` turns every remaining id
into a mandatory `capability:<id>` typed requirement, proven by the
`_CAPABILITY_RULES` reading of a card's authority and lifecycle. Those rules
bind capabilities to shapes: `implementation` needs modify authority or an
implementation lifecycle, `analysis` needs advise, plan or review authority,
`planning` needs plan authority or a planning lifecycle, `coordination` needs
a `coordination` lifecycle no card in the roster declares. When the planner
names a method that belongs to another shape, such as `implementation` on a
read-only review-report or `analysis` on a modify-authority test-code unit,
the only cards that can cover it are the wrong specialists for the unit, the
recruiter rightly leaves them out, and the deterministic gate rejects a
correct team. The captured plans of 2026-09-10 show the pattern on every
unit: `coordination` beside `implementation` on a merge, `operations` beside
`testing` on a push check, `verification` on every review.

Roster support makes the forcing sharp. Of 293 enabled contracts,
`coordination` is supported by 4, `threat-modeling` by 4, `operations` by 14,
`documentation` by 15, while `analysis` is supported by 248 and
`investigation` by 285. The compiler already carries six ad-hoc drops for
this (generic capabilities on implementation-change, `documentation` on a
plan, `data-analysis` on an analysis, ungrounded `automation`,
`communication` and `investigation`), each added after one observed failure.

Two records are missing beside the rule. The failure row names the axis and
the shortfall but never the requirement id left uncovered, so the 17 live
rows cannot say which capability forced the team. And no receipt names the
capabilities the compiler dropped, so a demotion is invisible after the fact.

## Current state

Filed from the AR-438 measurement of 2026-09-11. Not repaired.

## Approach

Bind a unit's mandatory capabilities to its own artifact shape (ADR-0252).
In the compiler, keep a planner-named capability only when the ontology's
support rule can be satisfied by a card whose typed shape is the unit's own:
its artifact kind, lifecycle phase, an authority that satisfies the unit's
authority, and its domains. A capability with no broad rule (a specialist
skill such as `threat-modeling` or `simulation`) and a declared novel
capability stay mandatory, so the roster-gap and hiring path is unchanged.
Drop the rest at compile time and record every dropped id on the applied
planner attempt as a closed receipt row in both durable receipts. Leave the
recruiter, the verifier, eligibility, the critic and the validators as they
are; no fallback and no advisory tier.

## Dependencies

AR-394 supplies the shortfall vocabulary the measurement reads. AR-438
supplies the two-unit population this must staff. ADR-0198 keeps waiving what
the roster cannot serve at all; this issue is about what the roster can serve
only with the wrong specialist.

## Acceptance

- [ ] A planner-named capability whose support rule cannot be met by a card of
      the unit's own shape is dropped by the compiler, and one whose rule can
      be met, one without a broad rule, and a declared novel capability are
      kept; the observed shapes (`implementation` on a review-report,
      `analysis` on a test-code unit, `coordination` on an implementation
      change, `planning` on an analysis) are pinned, and the existing
      compiler drops still hold.
- [ ] Every dropped capability reaches both durable receipts as a closed row
      on the applied planner attempt, and a malformed row projects blank
      rather than partially; the focused, named fast and decision-conformance
      checks pass.
- [ ] One fresh native run per host on the ordinary-review wording after the
      reinstall staffs with no `staff_without_safe_team` row on the capability
      axis, with the demotion rows recorded against the 17-row population.
