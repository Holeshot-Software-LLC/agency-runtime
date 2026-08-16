---
title: "Where the planner exceeds the vision, and what it costs"
status: draft
category: roadmap
created: 2026-08-16
updated: 2026-08-16
tags: [roadmap, vision, planner, staffing, eligibility, AR-119, decision-needed]
related:
  - docs/roadmap/AR-119-founding-vision.md
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-253-dynamic-team-dispatch-on-every-harness.md
  - docs/roadmap/issue-AR-255-inference-owned-host-proven-child-staffing.md
  - docs/decisions/0118-require-inference-owned-staffing.md
  - agency_runtime/core/workforce/intent.py
  - agency_runtime/core/workforce/planning_contracts.py
  - agency_runtime/core/workforce/staffing_verifier.py
supersedes: []
superseded_by: null
type: reference
issue_id: AR-119
---

# Where the planner exceeds the vision, and what it costs

An owner question on 2026-08-16: *is "planner" just a word for using inference
to find the intent of the ask?* If so it has to stay, as long as it does not
interfere with host dynamics.

The answer is **half yes**, and the other half is the source of three separate
staffing failures in the last two days. This document separates the two halves
so the direction can be chosen deliberately.

## The planner does two jobs, not one

`COMPACT_INTENT_SYSTEM` opens: *"You are Agency's intent planner. Think like a
senior engineering lead decomposing work into a governed specialist team."*

**Job one — read the intent.** A model call reads the request and characterises
it: what kind of artifact, which capabilities, which domains, which lifecycle
phase. This is exactly what the owner described, and the vision requires it in
so many words:

> Selection comes from INTENT, not keywords. Picking an agent must follow what
> the user actually means, not which words they used.

Job one is not negotiable and nothing here proposes touching it.

**Job two — decompose and constrain.** The same call also splits the request
into work units and attaches hard requirements to each. `WorkUnit` carries 17
fields, including `required_tools`, `platforms`, `domains`,
`required_capabilities`, `authority` and `mutation_scope`. These are not
descriptions. They become **hard eligibility gates** in `_eligibility`, which
can reject every candidate the recruiter ranked.

The founding vision contains **zero occurrences** of "plan" or "work unit". Its
card metaphor is: read what was just asked, pull the right card(s) from the
cabinet, hand them to whoever is about to do the work. There is no decomposition
step, and no notion of a unit that specialists must qualify against.

## What job two has cost, in evidence

Three failures in two days, all from constraints the planner invented rather
than from anything the request or the roster lacked.

1. **Invented domains (2026-08-15).** The planner emitted a domain no contract
   declares. Coverage is conjunctive, so one unknown domain defeats every
   possible ranking. Fixed by refusing unknown domains at the plan boundary,
   with an exception for `novel_capability` so rule 6 hiring stays reachable.
2. **The uncoverable-axis field could not see this class of fault
   (2026-08-16).** `_uncoverable_requirement_axis` reads
   `typed_staffing_coverage`; rejection happens in `_eligibility`. They are
   different checks over different fields, so a unit whose `required_tools` or
   `platforms` exclude every contract reports **no uncoverable axis at all** —
   which is precisely the signature the live canary produced.
3. **The tool gate emptied the child's universe (2026-08-16).** Unproven tool
   capability rejected **250 of 283** cards as
   `tool_capabilities_unproven:unknown`, leaving 33 tool-free specialists —
   `anthropologist`, `historian`, `narratologist` — for a Python regression
   review. The model correctly answered that none fits. Proving the host's
   capability raised it to 64.

## Why tools should not gate which card is pulled

A card is a prompt. Injecting the `code-reviewer` prompt requires nothing of the
host. Filtering the cabinet by tool capability decides **what expertise the model
is allowed to be told about**, which does not follow from anything in the vision.

The codebase already concedes half of this. `_eligibility` carries an explicit
comment that a specialist's own declared tool classes are *descriptive metadata,
not a hard eligibility failure*, because re-gating on them "rejects the model's
best-coverage specialist when it owns an optional surface the host doesn't
advertise". Only the **unit's** required tools remain as a gate — and the unit is
the planner's own invention. Remove job two's requirement synthesis and the gate
has nothing left to test.

There is a legitimate residue. Tool capability is real information about
**authority**, not expertise: it is reasonable not to tell a worker it may
rewrite the repository when it demonstrably cannot. That belongs in a line of
the card's instructions, not in a filter over which card gets pulled.

For the record, `_required_tools` is deterministic, derived from `artifact` and
`mutation_scope`, and only ever emits `repository-read`, `repository-write`,
`code-execution` and `test-execution` — all proven by this host's capability
receipt. So `agent_tools_missing` is probably **not** what killed the last
canary. The `top_ranked_ineligibility` field added in `7a399415` will name the
actual gate on the next run.

## The owner's test: does it interfere with host dynamics?

Job one does not. It reads a request and returns a characterisation; the host
still decides what to run and whether to spawn.

Job two does, in one specific way. When its synthesised constraints exclude
every candidate, Agency returns no cards **and the turn fails preflight**. That
is not complementing the agent — it is Agency's own invented requirement
withholding the capability. Rule 8's sharpened form permits a *verifier's
definite negative* to block; it does not sanction blocking because a planner
invented a constraint the roster cannot satisfy.

## Three directions

**A. Keep job one, delete job two's gates.** The planner still reads intent and
still characterises the request; its output becomes evidence handed to the
recruiter rather than hard eligibility. `_eligibility` keeps only facts about the
worker and the host — disabled, contract binding, host support — and drops
unit-derived tool, platform and domain gates. Closest to the vision. Largest
blast radius: `typed_staffing_coverage`, the six-axis conjunctive sufficiency
check, and every test asserting a unit can reject a candidate.

**B. Keep both, make job two advisory.** Constraints stay in the plan and stay
visible to the recruiter as ranking signal, but cannot by themselves produce an
empty team. Deterministic code still rejects genuinely unrunnable workers.
Smaller change, keeps multi-unit decomposition for rule 3 and rule 6, and removes
the "invented constraint blocks the turn" failure mode. Does not answer whether
decomposition should exist at all.

**C. Leave it and keep instrumenting.** Continue naming each new gate as it
fires — the `requirement_axis`, `ranked_agent_ids` and `top_ranked_ineligibility`
path. Cheapest, and it is what produced this document. But it has now cost three
diagnoses, and each new field only names the *next* invented constraint.

## Recommendation

**B now, A as the target**, with C's instrumentation kept because it is what
tells us whether A is safe.

B is reversible, unblocks the concrete Rule 4 path, and directly removes the
failure mode that has consumed two days. A is where the vision points, but it
touches the conjunctive sufficiency model that AR-253's acceptance criteria are
written against, and that should not be rewritten in the same change that is
trying to produce a first green Installed cell.

## Settled 2026-08-16: it binds through coverage, not eligibility

The `470ebf3b421a` canary returned `top_ranked_ineligibility` **absent** on both
rejected attempts, with `code-reviewer` ranked first. The top-ranked candidate
was executable, so no eligibility gate emptied the team, and direction B as
originally framed would have fixed nothing.

The binding constraint is still a planner invention, but it is the unit's
**conjunctive six-axis requirement set**, applied by
`_minimum_team_with_required` to the ranked candidates rather than by
`_eligibility` to each candidate. `selected` is computed, not model-supplied:
the search returns nothing when no combination of ranked executable candidates
covers every requirement within `max_selected_per_unit`.

This narrows all three directions:

- **B must target coverage**, not eligibility. Making unit `required_tools` and
  `platforms` advisory changes nothing; the requirement axes are what bind.
- **A is unchanged in principle** and now clearly larger: removing the unit's
  requirement synthesis means removing the conjunctive sufficiency model that
  AR-253's acceptance criteria are written against.
- **C got cheaper and better aimed.** The axis is now computed over the ranked
  set, so it names the axis a bounded repair can actually act on.

The immediate step taken was C: scope `_uncoverable_requirement_axis` to the
ranked contracts. Roster-wide uncoverability is a strict subset of it, so no
diagnostic power is lost. Whether the conjunctive requirement set should exist
at all remains open, and should be decided on the next live failure that names
a specific axis rather than on argument.

## What would settle it

One canary run carrying `top_ranked_ineligibility`. If it names a unit-derived
gate — `agent_tools_missing`, `agent_platform_unsupported` — job two is
confirmed as the live blocker and B becomes urgent. If it is absent, the
top-ranked candidate was executable and the recruiter declined it anyway, which
is a model or prompt problem in the recruiter and leaves the planner question
open but not urgent.
