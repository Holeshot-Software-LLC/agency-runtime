---
title: "Batch the recruiter call at two units"
status: accepted
category: decisions
created: 2026-09-11
updated: 2026-09-11
tags: [workforce, recruiter, inference, staffing]
related:
  - docs/roadmap/issue-AR-441-the-recruiter-answers-a-whole-expanded-plan-in-one-call.md
  - docs/decisions/0251-cap-ordinary-asks-at-two-planned-units.md
  - docs/decisions/0202-read-the-recruiter-reply-where-no-safety-property-lives.md
  - docs/decisions/0118-require-inference-owned-staffing.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
id: ADR-0254
type: decision
deciders: [owner]
---

# ADR-0254: Batch the recruiter call at two units

## Status

**Accepted 2026-09-11.** Owner direction: strict staffing must work and no
fallback may hide a failure; the recruiter picks specialists from a
determined pool, and the pool it is shown should fit in one answer.

## Context

The recruiter is asked once for every unit of the plan. The two blocks
that dominate its prompt, the typed recall rows and the detail cards, grow
with the unit count: a five-unit code mutation produced 77 to 95 KB prompts
in two samples on 2026-09-11, and in both the first reply did not carry
every row. Since 2026-09-08 `missing_work_unit` was the recruiter's most
frequent rejection (59 rows on 13 turns, all of which ended there), and
each repair spends a call the critic also needs. ADR-0251 removed the
ordinary asks from that exposure by capping them at two units, which is
where the recruiter succeeds; the plans the policy expands keep their
shape and their prompt.

## Decision

1. **At most two units per recruiter call.** `RECRUITER_UNITS_PER_CALL` is
   two. A plan of one or two units is recruited exactly as before. A larger
   plan is recruited in batches of at most two units in plan order, which
   is dependency order, so a unit's dependencies are already staffed when
   its batch is asked.
2. **A batch prompt is the same document, sliced.** It carries the whole
   plan, the host context, the authoritative bindings and the response
   contract, but only its own units' typed recall rows, the detail cards
   those rows and the hybrid evidence for those units reference, and the
   validated rows of the earlier batches as `earlier_batches`, so the
   recruiter keeps a reviewer independent of the implementers it already
   chose. The response contract names only the batch's units.
3. **One reader, one proposal, one verification.** Every batch's rows land
   in the same accumulator the bounded repair uses (ADR-0202); a batch reply
   that omits, misnames or malforms a unit is repaired for that unit only,
   within that batch's call. After the last batch the whole team is
   assembled and verified once, and a verifier finding re-asks only the
   failed units with the same feedback as today. Rows from different
   providers may meet in one proposal because the verifier judges the
   merged team deterministically.
4. **Budget decides the batch count, never the outcome.** When the
   remaining strict budget, less the critic's reserve, cannot afford one
   call per pair, the batches are widened evenly to the calls it can afford;
   the receipt's recruiter attempt count shows how many were made. The
   cache identity is the unsliced document, so a cached proposal is reused
   whole.
5. **Nothing else moves.** The verifier, the critic, the validators, the
   hiring path and the receipt vocabulary are unchanged.

## Consequences

- A five-unit plan costs three recruiter calls of roughly a third of the
  size instead of one call that has needed two; the budget spends the same
  or fewer calls when the single call would have been repaired.
- The recruiter no longer sees every unit's candidates at once; a
  cross-unit judgement it made from the whole team now relies on the
  earlier batches' rows it is shown, and the verifier and critic still judge
  the whole.
- Batches are visible only as attempt counts; a receipt row naming the
  batch's units is a follow-up.
