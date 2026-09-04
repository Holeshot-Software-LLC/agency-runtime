---
title: "AR-387: The recruiter sees cards without their eligibility, so it staffs implementers on plan units and misses the eligible planners"
status: in_progress
category: roadmap
created: 2026-09-03
updated: 2026-09-03
tags: [workforce, recruiter, staffing, inference, receipts]
related:
  - docs/decisions/0203-show-the-recruiter-the-complete-eligible-card-set-per-unit.md
  - docs/roadmap/issue-AR-384-staff-decisions-die-on-uncoverable-typed-requirements.md
  - docs/roadmap/issue-AR-373-recruiter-evidence-vocabulary.md
  - docs/roadmap/issue-AR-383-inferred-subject-context-fails-its-own-projection.md
  - docs/roadmap/issue-AR-336-requalify-the-recruiter-route-for-ordinary-tasks.md
supersedes: []
superseded_by: null
type: issue
epic: reliability
issue_id: AR-387
priority: p1
tracker_url: null
depends_on: []
blocks: []
---

# AR-387: The recruiter sees cards without their eligibility, so it staffs implementers on plan units and misses the eligible planners

## Problem

After ADR-0198, ADR-0201 and ADR-0202 the install path loses turns only to
judgment, and the largest recruiter-side judgment loss has a mechanical
cause. On the ADR-0201 run (2026-09-03, eleven install wordings, strict
mode) turn 201's plan-authority unit `unit-install-approach`
(`[operations, software-engineering]`) was staffed twice as

    desktop-app-engineer (required), cross-platform-installer-engineer,
    devops-automator, operations-manager

and rejected twice with `staff_without_safe_team:domain`, missing
`domain:software-engineering`. Three of the four ranked cards are
modify-authority implementers, ineligible for a plan unit; the only eligible
one, `operations-manager`, covers `operations` but not `software-engineering`;
`sre-site-reliability-engineer` and `it-service-manager`, eligible and
declaring both domains, sat unranked in the unit's recall rows.

The recruiter could not have known. Its document carried 86 `detail_cards`
(`agent_id`, `display_name`, `outcomes`, `scope_qualifiers`, `not_for`; no
authority, no eligibility) as the union of every unit's bounded recall rows,
and 24 `typed_recall` rows for the unit with `execution_eligible` flags. The
three implementers had cards because the implementation unit's rows recalled
them, and no row for the plan unit mentioned them at all; the prompt's own
words, "omission is not exclusion", told the recruiter that an absent row
proves nothing. It read three install-flavoured cards and ranked them.

Across the AR-386, ADR-0201 and ADR-0202 runs, every `staff_without_safe_team`
on a plan unit (five) had an eligible coverer of the missing token unranked in
the recall rows, and in four of the five the ranked candidates included cards
with no eligibility flag anywhere in the document.

## Current state

**Implemented on branch `claude/ar387-recruiter-eligibility` (2026-09-03)**
per [ADR-0203](../decisions/0203-show-the-recruiter-the-complete-eligible-card-set-per-unit.md):
every `typed_recall` row carries `eligible_candidate_ids`, the verifier's own
eligibility over the detail cards, complete for the unit and identity-sorted
(a boundary, never a ranking), plus `eligible_candidates_without_card`; the
safe-team repair contract carries `eligible_coverers_by_requirement`, the
eligible cards covering each requirement the ranked executable team left
uncovered (bounded to eight per token, identity-sorted); and both recruiter
prompts say that a card outside the list can be forbidden or omitted but
never staffed, while the repair guidance says an excluded candidate can be
neither required nor acceptable. On the installed roster the eligible card set
of a plan or review unit is the whole eligible roster (6 to 20 cards); the
lists add two to four kilobytes to a prompt of 67 to 82.

Alongside, the strict critic's run-to-run variance on an identical team was
measured by replaying two captured turn-205 critic calls six times each with
the gateway cache bypassed: the ADR-0201 prompt was approved six of six, the
ADR-0202 prompt (same team, different plan wording) vetoed
`wrong-neighbor-selection` five of six. The critic is mostly consistent per
prompt; the flip between runs was the prompt, not sampling.

Live re-measurement, the same eleven install wordings under strict mode on
the branch runtime against the reconciled store copy (evidence in
`docs/roadmap/acceptance/evidence/AR-387-evidence-20260903.txt`):

| outcome | turns |
|---|---|
| plan-authority units answered; ranked cards outside `eligible_candidate_ids` | 8; **0** |
| `staff_without_safe_team`, any unit | **0** (five plan-unit failures on the AR-386 run, two on the ADR-0201 run) |
| completed with a staffed team, critic approved | 5 (201, 204, 206, 207, 304); ADR-0202 run 4, ADR-0201 run 3, AR-386 run 2 |
| strict critic `wrong-neighbor-selection` | 3 (203, 205, 208) |
| recruiter replies the transport could not read | 2 (209 repair, 305) |
| recruiter reply shapes recorded and repaired | 3 (202, 209, 304's `invalid_decision`) |

On every plan unit the recruiter ranked exactly the eligible operations
planners; turns 201 and 304, both lost on the previous run, completed. What
remains is the critic's judgment on install teams, the deployment's replies
the transport cannot read, and turn 205's team, which the critic approves or
vetoes depending on the plan wording (section 5 of the evidence).

## Approach

Show the recruiter the hard boundary the runtime enforces, in full, per unit,
and name the eligible coverers when a repair is needed. Deterministic facts
only: no ranking, no recommendation, no filtering of the cards. The
alternatives, a per-card `authority` with a prose compatibility table, a
deterministic filter of ineligible cards, or a complete eligible card set
without regard to the prompt size, are recorded in ADR-0203.

## Dependencies

- AR-336 owns recruiter qualification; this removes the mechanical half of
  its plan-unit failures.
- AR-384 (done) supplies the waiver that makes a plan unit staffable once the
  right eligible card is ranked.

## Acceptance

- [x] Every `typed_recall` row the recruiter receives carries the complete,
      identity-sorted list of detail cards the runtime can staff on that unit,
      and the count of eligible workers without a card.
- [x] A `staff_without_safe_team` repair contract names the eligible cards
      covering each requirement the ranked executable team left uncovered.
- [x] Both recruiter prompts state that a card outside the unit's eligible
      list can be forbidden or omitted but never staffed.
- [x] On the same eleven install wordings under strict mode, no plan-authority
      unit is rejected `staff_without_safe_team` while an eligible coverer of
      the missing token was among the detail cards.
