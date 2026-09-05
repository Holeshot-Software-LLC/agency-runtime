---
title: "AR-393: A declared capability gap can leave no hiring account at all, and when it leaves one the reasons need not explain it"
status: open
category: roadmap
created: 2026-09-04
updated: 2026-09-04
tags: [workforce, hiring, receipts, observability, staffing]
related:
  - docs/roadmap/issue-AR-378-hiring-failure-records-no-attempt.md
  - docs/roadmap/issue-AR-384-staff-decisions-die-on-uncoverable-typed-requirements.md
  - docs/roadmap/issue-AR-392-transport-failures-collapse-to-one-code.md
  - docs/roadmap/issue-AR-304-preserve-recruiter-critic-validation-diagnostics.md
  - docs/roadmap/handoffs/issue-AR-383.md
  - docs/decisions/0198-waive-the-typed-requirements-the-roster-declares-but-cannot-serve.md
  - agency_runtime/core/selector/pipeline.py
  - agency_runtime/core/workforce/inference.py
  - agency_runtime/core/preflight_failure.py
supersedes: []
superseded_by: null
type: issue
epic: observability
issue_id: AR-393
priority: p1
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/650
depends_on: []
blocks: []
---

# AR-393: A declared capability gap can leave no hiring account at all, and when it leaves one the reasons need not explain it

## Problem

The AR-383 recovery capsule recorded an unexplained observation: across 45
preflight receipts, `no_safe_sufficient_team` was declared five times and
hiring events appeared once, so four of five declared gaps produced no
hireable gap unit, and `_all_gap_units` / `_hireable_gap_units` were named as
where that divergence lives. It is real, it is larger than five samples, and
it has two distinct halves.

**A declared gap can vanish before anything records it.** `_all_gap_units`
(`agency_runtime/core/selector/pipeline.py:1487`) intersects the verifier's
`no_safe_sufficient_team` unit ids with `outcome.plan.units`. When that
intersection is empty, `_complete_gap_hiring_events` (`:1502`) has nothing to
iterate, `routing["hiring_events"]` is never set because the projection only
assigns it when the list is non-empty (`:1934`), and
`preflight_hiring_reason_codes` (`preflight_failure.py:337`) reads an absent
key as `[]`. The receipt then declares a capability gap in
`staffing_reason_codes` and says nothing whatsoever about hiring. Nothing
distinguishes that from a turn where hiring was never relevant.

**When a gap does reach the receipt, the reasons given need not be the
reason.** `_hireable_gap_units` (`:1393`) narrows the gap units three ways
and returns only the survivors, discarding which test each casualty failed:

- a single **global** abstention code outside the allowed set returns the
  empty tuple for the whole turn (`:1412`), disqualifying every unit at once;
- a unit whose proposal row does not carry `inference-declared-gap` is
  dropped (`:1414`);
- a unit with a code of its own outside the allowed set is dropped (`:1431`).

`_complete_gap_hiring_events` then labels every survivor of none of these
`gap_evidence_not_hireable` followed by that unit's *own* verifier codes
(`:1525`). Only the third case is self-explaining. In the first two the
listed codes are all inside the allowed set, so the evidence printed on the
event disqualifies nothing, and the thing that actually disqualified the unit
-- a global code, or a missing declaration -- is never named anywhere.

## Current state

**Measured on the live store**, `~/.agency-runtime/agency.db` read-only,
2026-09-04, 993 `preflight_failure_receipts`:

| | receipts |
|---|---|
| declaring `no_safe_sufficient_team` | 99 |
| of those, **empty `hiring_reason_codes`** | **42** |
| of those, some hiring account | 57 |

- 41 of the 42 are stage `routing`, reason `substantive_specialist_unavailable`;
  one is `workforce_inference_failed`.
- **Every one of the 42 carries a staffing code set drawn entirely from
  `_INFERRED_GAP_VERIFIER_CODES`** (`workforce/inference.py:3622`): 31 carry
  exactly `no_safe_sufficient_team` + `recruiter_abstained`, the pair
  `_valid_inferred_gap_proposal` (`:3634`) demands of every declared unit; the
  rest add `independent_assurance_missing`, `required_agents_missing` or
  `roster_coverage_gap`, all of which are in that set. These are the turns the
  governed hiring path exists for, and they are the ones it says nothing about.
- Not host-specific: codex 30, claude 5, openclaw 4, hermes 3. Not the
  activation canary either, whose projection sets `hiring_events = []`
  deliberately (`pipeline.py:1908`) but requires an exact codex canary task
  string, which cannot account for the twelve non-codex receipts.
- Not historical: the empty receipts run 2026-08-29 to 2026-09-03, interleaved
  with filled ones on the same days.
- The "hiring was not allowed" case is already reported -- 20 receipts say
  `hiring_status_not_attempted` + `hiring_requires_inferred_gap` -- which is
  what makes the 42 a different silence rather than the same one.

**Reproduced in process** at `77a595b9` (`scratchpad/gapprobe.py`; these three
functions are pure over a duck-typed outcome, so no provider is involved):

| case | `_all_gap_units` | `_hireable_gap_units` | receipt events |
|---|---|---|---|
| plan absent, reasons name the unit | `()` | `()` | **none at all** |
| proposal row not `inference-declared-gap` | `('u1',)` | `()` | `gap_evidence_not_hireable, no_safe_sufficient_team, recruiter_abstained` |
| one **global** `selection_confidence_too_low`, two units, both units' own evidence clean | `('u1','u2')` | `()` | both units: `gap_evidence_not_hireable` + their own allowed codes; the global code on neither |

The second and third rows print evidence that cannot support the verdict. The
first prints nothing.

**Not yet established:** which of the three conditions produced the 42.
`_all_gap_units` matches the verifier's reason unit ids against
`outcome.plan.units`, and the leading candidate is that a repair re-planned
the turn, leaving the retained staffing decision referencing the first plan's
unit ids while `outcome.plan` carries the second's. Separating that from an
absent plan needs a live reproduction from a shell with the credential
sourced; the receipt as it stands cannot answer it, which is the issue.

## Approach

Proposed; an ADR accompanies the implementation.

1. **A declared gap may never be dropped silently.** Every
   `no_safe_sufficient_team` reason gets an event, including one whose unit id
   matches no plan unit, carrying a code that says exactly that. If the plan
   was replaced under the decision, the receipt should say so rather than
   omit the unit.
2. **`_hireable_gap_units` should return the disqualifier, not just the
   survivors.** A per-unit verdict -- global code, missing declaration, or the
   unit's own code -- lets `_complete_gap_hiring_events` name the test that
   failed instead of relabelling codes that passed.
3. **The global gate must name itself.** One global code outside the allowed
   set disqualifies every unit on the turn; that code belongs on every event
   it disqualified, since no unit's own evidence explains the outcome.
4. **`gap_evidence_not_hireable` should not be the label on the final
   branch** (`:1535`), which is reached with the unit *in* `current_hireable`.
   Lower confidence: the loop above may make that branch unreachable in
   production. It is reachable in the function itself, and a receipt code that
   contradicts the tuple it was computed from should not be written either
   way.

This is a receipts change. Nothing here selects, ranks, or hires differently;
the same units are hired and the same units are not.

## Dependencies

None. AR-378 established that a hiring stage which records nothing leaves the
receipt undebuggable and added the not-attempted events this issue extends;
ADR-0198 put `roster_coverage_gap` in the allowed set. Both are merged.

## Acceptance

- [ ] A turn whose staffing decision declares `no_safe_sufficient_team` for a
      unit always produces a hiring event for that unit, including when the
      unit id matches no plan unit, and the event names that condition.
- [ ] An event that reports a unit as not hireable names the test that
      disqualified it; when the disqualifier is a global code, that code is on
      the event.
- [ ] `gap_evidence_not_hireable` appears only on events whose listed codes
      include at least one code outside the hireable set.
- [ ] Replaying the shapes in the table above produces an event for every
      declared gap, and no event whose reason codes are all inside the
      allowed set.
- [ ] Measured live from a shell with the credential sourced: the count of
      receipts declaring `no_safe_sufficient_team` with empty
      `hiring_reason_codes` is zero, and the condition behind the 42 is named
      on the receipts that carried it.
