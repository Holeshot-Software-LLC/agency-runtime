---
title: "Batch the recruiter call at two units"
status: proposed
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

**Proposed 2026-09-11.** Owner direction: strict staffing must work and no
fallback may hide a failure; the recruiter picks specialists from a
determined pool, and the pool it is shown should fit in one answer. The
branch is complete and reviewed; whether it merges is the owner's decision
on the measured trade below.

## Context

The recruiter is asked once for every unit of the plan. The two blocks
that dominate its prompt, the typed recall rows and the detail cards, grow
with the unit count: a five-unit code mutation produced 77 to 95 KB prompts
in two samples on 2026-09-11, and in both the first reply did not carry
every row. Since 2026-09-08 `missing_work_unit` was the recruiter's most
frequent rejection (59 rows on 13 turns; the bounded repair rescued 8 of
them and 5 failed, 4 at the recruiter), and each repair spends a call the
critic also needs. ADR-0251 removed the
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
   those rows' candidates, sole eligible coverers and hybrid additions
   reference (eligible ids are filtered to the cards shown and the rest
   counted), and the validated rows of the earlier batches as
   `earlier_batches`, so the recruiter keeps a reviewer independent of the
   implementers it already chose. The response contract names only the
   batch's units, and the batch is asked with a system prompt that asks for
   its listed units alone rather than for every planned unit.
3. **One reader, one proposal, one verification.** Every batch's rows land
   in the same accumulator the bounded repair uses (ADR-0202); a batch reply
   that omits, misnames or malforms a unit is repaired for that unit only,
   within that batch's call. After the last batch the whole team is
   assembled and verified once; a finding re-asks only the failed units in
   one scoped call whose document carries those units' own recall rows and
   cards and the same feedback the single-call repair receives, and the
   reply the verifier refused is recorded rejected with the verifier's rows.
   Rows from different providers may meet in one proposal because the
   verifier judges the merged team deterministically.
4. **Budget decides the batch count, never the outcome.** Every batch must
   afford one repair, and the whole-team repair after verification one more
   call, beside the critic's reserve: when the remaining strict budget
   cannot, the batches are widened evenly to what it can afford, down to
   the single call main makes (the shipped default budget of five leaves
   that single call; the owner machine's eight asks two batches for five
   units, nine asks three); the receipt's recruiter attempt count shows how
   many were made. The cache identity is the unsliced document, so a cached
   proposal is reused whole.
5. **Nothing else moves.** The verifier, the critic, the validators, the
   hiring path and the receipt vocabulary are unchanged.

## Consequences

- A five-unit plan is asked in two or three calls (by budget) whose measured
  sizes ran from 25 to 70 KB against one call of 77 to 95 KB; the 37, 41
  and 25 KB of the corrected-prompt sample came with a smaller recall draw,
  not a smaller slicer. A repair re-asks at most the failed units.
- The measured trade so far (same wording, same day, same deployment): the
  first draft, whose batches still carried the "every planned unit" system
  sentence, was rejected on 7 of 12 batch first replies against 2 of 2
  single calls, spent 3 to 6 recruiter calls where the single call spent 2,
  and two of its four turns met a critic veto; the corrected prompt was
  measured once (its twin was a gateway replay) and was accepted with 1
  rejection in 3 batch calls and 4 recruiter calls. The samples are too few
  to state a rate; the deployment rejects on reply shape at every size
  measured, and whether the smaller, scoped calls are worth their count is
  the owner's decision.
- The recruiter no longer sees every unit's candidates at once; a
  cross-unit judgement it made from the whole team now relies on the
  earlier batches' rows it is shown, and the verifier and critic still judge
  the whole.
- Batches are visible only as attempt counts; a receipt row naming the
  batch's units is a follow-up, as is the receipt's sixteen-attempt bound,
  which more recruiter calls per turn approach sooner.
