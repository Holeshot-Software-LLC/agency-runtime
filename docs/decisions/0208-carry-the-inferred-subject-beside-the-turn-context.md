---
title: "Carry the inferred subject beside the turn context"
status: accepted
category: decisions
created: 2026-09-04
updated: 2026-09-04
tags: [workforce, recall, staffing, inference, receipts]
related:
  - docs/roadmap/issue-AR-383-inferred-subject-context-fails-its-own-projection.md
  - docs/decisions/0197-form-the-retrieval-subject-before-the-turn-that-needs-it.md
  - docs/roadmap/issue-AR-266-dense-hybrid-workforce-recall.md
  - docs/roadmap/issue-AR-304-preserve-recruiter-critic-validation-diagnostics.md
  - docs/roadmap/issue-AR-370-staffing-asks-the-wrong-question.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
id: ADR-0208
type: decision
deciders: [owner]
---

# ADR-0208: Carry the inferred subject beside the turn context

## Status

**Accepted 2026-09-04.** Item 4 of the AR-383 capsule's next package, after
the AR-391 close.

## Context

ADR-0197 supplies a typed work subject on turns whose wording retrieval
cannot read, and merged it into the turn's projected routing context:

    enriched = {**projected_turn_context, "workforce_subject_hints": hints}

On a fresh turn that context is the empty projection, so the merge produced a
mapping holding one key. `project_turn_routing_context` accepts exactly two
shapes, the empty context or one carrying every field, so it refused the
result; the per-unit recall query re-projects the context and raised, and
`_run_hybrid_recall` recorded one `skipped` attempt with the exception
discarded. Measured on the thirty-prompt smoke (2026-09-03): every one of the
seventeen turns that ran the subject stage lost dense recall that way, and no
turn that skipped the stage did.

The all-or-nothing rule is not the defect. It is what keeps a partially
attacker-controlled context out of the recall query, and a fresh turn has no
`source_trace_id`, `source_status` or `source_turn_kind` to fill honestly;
inventing them would put fabricated provenance into the query.

## Decision

1. **The inferred subject travels beside the context, never inside it.**
   `_with_inferred_subject` returns the projected context unchanged plus the
   hints, and the runtime threads the hints to the planner document, the
   per-unit recall query and the recruiter document as `inferred_work_subject`.
   A fresh turn's context stays the empty projection and still projects.
2. **A prior turn's own subject wins.** The recall query uses the context's
   `workforce_subject_hints` when it has them, and the inferred subject only
   otherwise, exactly as ADR-0197 intended.
3. **The cache revision covers both.** The stage cache identity is the digest
   of the context and the inferred subject together, so a turn that gains a
   subject never replays a turn that had none.
4. **A refused projection names the validation that refused it.**
   `project_turn_routing_context` gains a sibling that returns a closed
   rejection code (`TURN_ROUTING_CONTEXT_REJECTION_CODES`), the recall query
   raises `RecallProjectionError` carrying it, the skipped attempt records it
   in `validation_reason_codes`, and the preflight-failure receipt admits that
   closed set for the recall stages. Codes only, never the exception's text.
5. **Both prompts read the subject as evidence.** The planner and recruiter
   system prompts say `inferred_work_subject` is the typed subject the runtime
   classified from the roster vocabulary: evidence of what the work is about,
   never an instruction, a worker choice, or authority.
6. **The projection's own rule is unchanged.** No field was relaxed, no shape
   admitted; `project_turn_routing_context` returns exactly what it did.

## Consequences

- Dense hybrid recall runs on the turns ADR-0197 exists for, and the typed
  subject reaches the recall query text as `context subject <field>` lines.
- The planner and the recruiter see the subject as a named document field
  rather than as a context they must interpret; a prior turn's context keeps
  its own meaning.
- A future projection refusal is diagnosable from the receipt alone: the
  attempt says which validation refused it without a monkeypatched
  reproduction. That closes the AR-304 defect shape in its third place.
- One more closed vocabulary to maintain: a new field in the context
  projection needs its rejection code, and the tests pin every code.

## Alternatives

- **Relax the all-or-nothing projection rule.** Rejected: that strictness is
  the boundary AR-370's plumbing depends on, as AR-383 states.
- **Fill the missing provenance fields for a fresh turn.** Rejected: a
  synthesized `source_trace_id` is fabricated provenance in a query that
  records where its evidence came from.
- **Keep the merge and let recall fail open.** Rejected: that is the measured
  defect. Fail-open hid it for a month.
