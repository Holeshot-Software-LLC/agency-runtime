---
title: "AR-441: The recruiter answers a whole expanded plan in one call"
status: open
category: roadmap
created: 2026-09-11
updated: 2026-09-11
tags: [workforce, recruiter, inference, reliability]
related:
  - docs/decisions/0254-batch-the-recruiter-call-at-two-units.md
  - docs/roadmap/issue-AR-438-cap-ordinary-asks-at-two-units.md
  - docs/decisions/0251-cap-ordinary-asks-at-two-planned-units.md
  - docs/roadmap/issue-AR-385-structured-reply-budget-truncates-nominations-silently.md
  - docs/decisions/0202-read-the-recruiter-reply-where-no-safety-property-lives.md
  - docs/roadmap/evidence/AR-441-recruiter-prompt-baseline-20260911.json
supersedes: []
superseded_by: null
type: issue
epic: reliability
issue_id: AR-441
priority: p1
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/887
depends_on: []
blocks: []
---

# AR-441: The recruiter answers a whole expanded plan in one call

## Problem

The recruiter receives one prompt for every unit of the plan and must
answer one row per unit. Since 2026-09-08 its most frequent rejection is
`missing_work_unit`: 59 unit rows on 13 turns, seven of them on codex. Eight
of those turns completed after the bounded repair rescued the omitted rows;
five failed, four of them at the recruiter and one at the critic (the first
record of this issue said all 13 ended at the recruiter; the review
measured it and the record was corrected). AR-438 removed the
ordinary-ask exposure by capping such plans at two units; since that
reinstall only one turn in 22 drew the code. The plans the policy still
expands keep their shape, and a code mutation is five units: discovery,
implementation, test-code, review-report and test-evidence.

Two in-process samples of that shape on 2026-09-11
([evidence](evidence/AR-441-recruiter-prompt-baseline-20260911.json)) show
what the recruiter is asked to hold. The prompt was 94,611 and 76,591 bytes;
in the second, `typed_recall` for the five units was 39,126 bytes and the 70
detail cards 34,488 bytes, against a 4,230-byte plan and a 1,205-byte
response contract. Both samples needed a second recruiter call before every
row arrived: the first reply was not JSON in one (`provider_model_text_not_json`
after 14.9 s) and arrived as a shape the row reader could not use in the
other, so all five units were recorded `missing_work_unit` and the bounded
repair asked for them again. Each of those calls spends one unit of the strict call budget
(8 on the owner machine, default 5) that the critic and any repair also
need; the turns that died at the recruiter since 2026-09-08 spent it on
the same omissions.

The reply budget work (AR-385) bounded the reply and the row reader
(ADR-0202) keeps whatever rows do arrive, so the runtime already repairs a
partial answer. What it never does is ask a smaller question. The prompt's
two largest blocks scale with the unit count, and the deployment that
serves the recruiter route drops or malforms rows under that load.

## Current state

Repaired on branch `claude/ar441-recruiter-batching-20260911` per ADR-0254:
`_recruiter_batches` splits a plan of more than two units into batches of
at most two in plan order, widened evenly when the remaining budget less the
critic's reserve cannot afford one call plus one repair per batch (the
shipped default strict budget of five leaves the single call main makes);
`_recruiter_batch_document` slices the recruiter document to a batch's
typed recall rows, the cards those rows' candidates, sole eligible coverers
and hybrid additions reference, and the earlier batches' validated rows; a
batch is asked with a batch-aware system prompt that names its listed units
only; the batch count also reserves the one whole-team repair call, so the
owner machine's budget of eight asks two batches for five units; `_NominationAccumulator` gains a batch scope; after the last batch the
whole team is assembled and verified once, and a finding re-asks only the
failed units in one scoped call whose document carries those units' recall
rows and cards, with the reply the verifier refused recorded rejected. A
one- or two-unit plan is recruited exactly as before. One
decision-conformance anchor moved to name the single-call site uniquely.

The first draft asked each batch with the unchanged recruiter system prompt,
whose "return one row for every planned unit, never omit a unit" contradicted
the batch contract, sized batches without repair headroom (a default-budget
host would have abstained on budget), and could not repair a finding on an
earlier batch's unit; the adversarial review found all three and they are
fixed in the second commit.

Measured in process
([evidence](evidence/AR-441-batching-in-process-20260911.json)): the
five-unit wording's batch prompts were 53 to 70, 47 to 51 and 25 to 33 KB in
the first-draft samples and 37, 41 and 25 KB in the corrected-prompt sample
(a different planner draw with fewer recall cards; the slice code did not
change) against 77 to 95 KB for the single call.
Under the first draft 7 of 12 batch calls were rejected on their first reply
(reply-shape failures) against 2 of 2 single calls, so batched turns spent 3
to 6 recruiter calls where the single call spent 2, and two of four were
then vetoed by the critic. Under the corrected prompt one independent turn
(its twin was a gateway replay) was accepted with 1 rejection in 3 batch
calls and 4 recruiter calls. Too few samples to claim a rate either way; the
records state the trade and the merge is the owner's call.

## Approach

Ask the recruiter for at most two units per call (ADR-0254). Batches follow
plan order, so a unit's dependencies are already staffed when its batch is
asked; each batch prompt carries the whole plan for context but only its
own units' typed recall, detail cards and hybrid evidence, the response
contract names only its units, and the validated rows of earlier batches
ride along so the recruiter can keep a reviewer independent of the
implementers it already chose. The rows accumulate in the same reader the
bounded repair uses; the whole team is assembled and verified once after
the last batch, and a verifier finding re-asks only the failed units, as it
does today. When the budget cannot afford one call per pair, batches are
widened to fit and the receipt shows it in the attempt count. Nothing in
the verifier, the critic, the validators or the receipts changes.

## Dependencies

AR-438 supplies the population this must staff (the expanded plans).
ADR-0202 supplies the row reader and repair contract the batches reuse.
AR-385 bounds each reply.

## Acceptance

- [ ] A plan of more than two units is recruited in batches of at most two
      in plan order, each batch prompt carrying only its units' typed recall,
      detail cards and hybrid evidence beside the whole plan and the earlier
      batches' rows; a plan of one or two units is recruited exactly as before.
- [ ] The rows of every batch assemble into one proposal that the existing
      verifier judges whole; a batch reply that omits or misnames a unit is
      repaired for that unit only; a verifier finding after the last batch
      re-asks only its failed units; the attempts, calls and cache identity
      account for every batch; the focused, named fast and
      decision-conformance checks pass.
- [ ] Fresh in-process runs of the five-unit code-mutation wording after the
      reinstall record the batch prompt sizes against the single-call size,
      the first-reply rejection count per batch call, the recruiter calls per
      turn and the outcome, beside the two baseline samples, and one fresh
      native run per host on that wording is recorded; the record states the
      measured trade whatever it is.
