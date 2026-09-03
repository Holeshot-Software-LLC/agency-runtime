---
title: "AR-383: The inferred subject context fails its own projection, so dense recall is silently skipped"
status: open
category: roadmap
created: 2026-09-03
updated: 2026-09-03
tags: [workforce, recall, staffing, inference, receipts]
related:
  - docs/decisions/0197-form-the-retrieval-subject-before-the-turn-that-needs-it.md
  - docs/roadmap/issue-AR-370-staffing-asks-the-wrong-question.md
  - docs/roadmap/issue-AR-266-dense-hybrid-workforce-recall.md
  - docs/roadmap/issue-AR-304-preserve-recruiter-critic-validation-diagnostics.md
supersedes: []
superseded_by: null
type: issue
epic: reliability
issue_id: AR-383
priority: p1
tracker_url: null
depends_on: []
blocks: []
---

# AR-383: The inferred subject context fails its own projection, so dense recall is silently skipped

## Problem

ADR-0197 landed `_with_inferred_subject` to supply a typed work subject on
turns whose wording retrieval cannot read. The enrichment it produces is
rejected by the same projection its own consumer applies, so the turn loses
dense hybrid recall entirely and the typed subject never reaches the recall
query it was built to enrich.

Measured 2026-09-03 on the installed runtime (`agency route --host codex`,
credential sourced), over the complete thirty-prompt smoke:

| | count |
|---|---|
| prompts | 30 |
| turns that ran the `subject` stage | 17 |
| of those, `subject` returned `status: applied` | 17 |
| of those, failed `dense_recall_projection_invalid` | **17** |
| turns that failed that way *without* the subject stage | **0** |

The correlation is total in both directions: 17 of 17, and 0 of the other 13.
Running the subject stage is sufficient to lose dense recall, and nothing else
on this box causes that failure.

For scale, 22 of the 30 turns did not staff at all, and 21 of those 22 abstained
on an inference-stage failure rather than a recruiter judgement
(`inference_invalid` 14, `inference_unavailable` 7, against one
`no_safe_sufficient_team` and one `recruiter_abstained`). This defect accounts
for 17 of them.

## Mechanism

Traced 2026-09-03, and reproduced directly rather than inferred.

`_with_inferred_subject` (`core/workforce/inference.py:3483-3518`) merges the
answer into whatever context the turn already had:

    enriched = {**projected_turn_context, "workforce_subject_hints": hints}

On a fresh turn — every turn AR-370 targets — `projected_turn_context` is
`{}`, so `enriched` is a **single-key mapping**.

`project_turn_routing_context` (`core/turn_routing_context.py:154-199`) accepts
exactly two shapes: the empty context, or one carrying the complete
`_TURN_ROUTING_CONTEXT_FIELDS` set. The gate is line 166,
`set(value) != _TURN_ROUTING_CONTEXT_FIELDS`. A mapping holding only
`workforce_subject_hints` is neither, so the projection returns `None`.

`project_unit_query` (`core/workforce/hybrid_recall.py:255-287`) re-projects
the context once per planned unit and raises at line 268:

    ValueError("turn_routing_context is malformed or unbounded")

`_run_hybrid_recall` catches `(TypeError, ValueError)` at
`core/workforce/inference.py:2045` and returns one `skipped` attempt carrying
`reason_code="dense_recall_projection_invalid"`.

Reproduced against the live roster with the real classifier answer:

    hints: {"domains": ["platform"], "languages": [], "frameworks": [],
            "capability_ids": ["operations"], "platforms": ["windows", "linux"]}
    project_turn_routing_context({"workforce_subject_hints": hints}) -> None

The hints themselves are well-formed and drawn from the roster vocabulary
exactly as ADR-0197 specifies. Dropping any single field changes nothing: the
rejection is of the envelope, not the payload.

## Consequences

1. **Dense hybrid recall is disabled on exactly the turns ADR-0197 exists to
   help.** AR-266 built that retrieval; a turn carrying an inferred subject
   silently falls back to whatever recall survives without it.
2. **The typed subject never reaches the per-unit recall query.** ADR-0197
   names three consumers — the planner document, the per-unit recall query
   through `hybrid_recall._context_fields`, and the recruiter document. The
   second is not reached, because the context that would carry it is the
   thing being rejected.
3. **The receipt cannot be debugged.** The `except (TypeError, ValueError)`
   discards the exception, so the attempt records `dense_recall_projection_invalid`
   and nothing about which field failed or why. That is the same defect shape
   as AR-304 and AR-378, in a third place.

## Current state

Filed from the AR-370 smoke re-run, not yet fixed. The failure is invisible in
normal operation: staffing continues, the turn returns, and only the attempt
roll shows a `skipped` dense recall. It did not surface earlier because the
prior smoke ran without a credential, so the subject stage never executed at
all and this path was never reached.

## Approach

Two independent changes; the first is the defect, the second is why it took a
live trace to find.

1. **Make the enrichment produce a projectable context.** The merge must emit
   either a complete `_TURN_ROUTING_CONTEXT_FIELDS` context or carry the
   subject hints on a channel that does not pretend to be a turn context. The
   choice is real and belongs in the decision record, because a fresh turn has
   no `source_trace_id`, `source_status` or `source_turn_kind` to honestly
   fill: inventing them to satisfy a schema would put fabricated provenance
   into the recall query. Carrying the hints beside the context, rather than
   inside it, is the shape that does not require inventing a source turn.
2. **Preserve the rejected projection's reason.** The attempt should record
   what failed validation, bounded and content-free, so a future occurrence is
   diagnosable from the receipt instead of from a monkeypatched reproduction.

Retiring the all-or-nothing rule in `project_turn_routing_context` is
deliberately **not** proposed. That strictness is what keeps a partially
attacker-controlled context from reaching the recall query, and AR-370's own
plumbing depends on it.

## Secondary observation, not diagnosed here

The subject stage fired on **17 of 30** turns. ADR-0197 costed the
gate at **7 of 30** against the roster-wide lexical scorer, and turns that
score normally against the full 291-card roster still ran the stage. The
pipeline gate reads `request.catalog`, which is not necessarily the catalog the
ADR measured. That discrepancy is recorded here as an observation and needs its
own investigation; this issue does not claim a cause for it.

## Dependencies

- ADR-0197 owns the enrichment this issue reports as unprojectable.
- AR-370 cannot demonstrate its retrieval acceptance while this holds, because
  the typed subject it produces does not reach the recall query.

## Acceptance

- [ ] A turn whose only context is an inferred subject projects successfully,
      and no turn that runs the subject stage records
      `dense_recall_projection_invalid`.
- [ ] The typed subject reaches the per-unit recall query, demonstrated by the
      rendered query text carrying the inferred fields.
- [ ] A rejected projection records, in the attempt, which validation failed,
      without carrying request content.
- [ ] A regression test pins the fresh-turn shape specifically: the enrichment
      of an empty context is projectable, so this cannot silently return.
- [ ] A smoke re-run over the same prompt set reports zero
      `dense_recall_projection_invalid` attempts.
