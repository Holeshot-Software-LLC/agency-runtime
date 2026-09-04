---
title: "Account for every declared gap"
status: accepted
category: decisions
created: 2026-09-04
updated: 2026-09-04
tags: [workforce, hiring, staffing, receipts, observability]
related:
  - docs/roadmap/issue-AR-393-declared-gaps-leave-no-hiring-account.md
  - docs/roadmap/issue-AR-378-hiring-failure-records-no-attempt.md
  - docs/roadmap/handoffs/issue-AR-383.md
  - docs/decisions/0198-waive-the-typed-requirements-the-roster-declares-but-cannot-serve.md
  - docs/decisions/0209-name-the-transport-cause-instead-of-one-code.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
id: ADR-0210
type: decision
deciders: [owner]
---

# ADR-0210: Account for every declared gap

## Status

**Accepted 2026-09-04.** Item 2 of the AR-383 capsule's next package, filed
as AR-393, implemented beside ADR-0209.

## Context

Measured on the live store on 2026-09-04 across 993 preflight receipts: 99
declared `no_safe_sufficient_team`, and 42 of those carried empty
`hiring_reason_codes`. Every one of the 42 carried a staffing code set drawn
entirely from the verifier codes that describe why a gap is real -- 31 carried
exactly `no_safe_sufficient_team` and `recruiter_abstained`, the pair a valid
inferred-gap proposal demands of every declared unit. These are the turns the
governed hiring path exists for, and they are the ones it said nothing about.
The silence was not host-specific and not historical, and the "hiring was not
allowed" case was already reported separately, which is what made the 42 a
different silence rather than the same one.

Two halves produced it.

**A declared gap could vanish before anything recorded it.** `_all_gap_units`
intersected the verifier's `no_safe_sufficient_team` unit ids with
`outcome.plan.units`. When that intersection was empty,
`_complete_gap_hiring_events` had nothing to iterate, `hiring_events` was never
set on the routing projection because it is assigned only when the list is
non-empty, and `preflight_hiring_reason_codes` read the absent key as `[]`. The
receipt declared a capability gap and said nothing whatsoever about hiring,
indistinguishable from a turn where hiring was never relevant.

**When a gap did reach the receipt, the reasons given need not have been the
reason.** `_hireable_gap_units` narrowed the gap units three ways and returned
only the survivors, discarding which test each casualty failed: a single global
abstention code outside the allowed set disqualified every unit at once; a unit
whose proposal row did not carry `inference-declared-gap` was dropped; and a
unit with a code of its own outside the allowed set was dropped. Only the third
is self-explaining. In the first two every listed code is inside the allowed
set, so `gap_evidence_not_hireable` followed by the unit's own codes printed
evidence that disqualified nothing, and the thing that actually disqualified
the unit was named nowhere.

## Decision

1. **A declared gap may never be dropped silently.** `_all_gap_units` returns
   every unit the staffing decision named, including one whose id matches no
   plan unit, which carries `gap_unit_absent_from_plan`. If a repair replaced
   the plan under the retained decision, the receipt says so rather than
   omitting the unit.

2. **`_hireable_gap_units` returns the disqualifier, not just the survivors.**
   One function, `_gap_hiring_verdicts`, computes a per-unit verdict, and both
   the survivor list and the event builder read it. An empty verdict means
   hireable; the survivors are exactly the units with no disqualifier, so the
   two answers cannot drift apart.

3. **The global gate names itself.** One global code outside the hireable set
   disqualifies every unit on the turn, so `gap_global_abstention_code` and
   that code travel onto every event it disqualified. No unit's own evidence
   explains that outcome.

4. **`gap_evidence_not_hireable` means what it says.** It appears only when the
   unit's own codes include one outside the hireable set, and only then are
   those codes listed after it. The final branch, reached with the unit still
   hireable and no limit met, carries `gap_hire_not_attempted`: the old code
   there contradicted the tuple it had just been computed from.

5. **No event lists only codes that support the opposite conclusion.** This is
   the rule the four codes above share, and it is asserted over all of the
   reproduced shapes rather than case by case.

## Consequences

A receipt that declares a capability gap now always carries a hiring account,
and the account names the test that failed rather than the evidence that
passed. The count of receipts declaring `no_safe_sufficient_team` with empty
`hiring_reason_codes` should be zero among receipts written after this change;
the 42 already stored are history and are not rewritten, so the measurement is
over new receipts with the 42 kept as the before-baseline.

Which of the three conditions produced the live 42 is still not established.
The leading candidate is a repair re-planning the turn while the retained
staffing decision references the first plan's unit ids, which is now
`gap_unit_absent_from_plan` and will name itself on the next receipt that hits
it. Separating that from the other two was impossible from the receipt as it
stood, which is the issue.

Nothing here selects, ranks or filters a specialist. The change is in what the
runtime records about a gap it already declared.
