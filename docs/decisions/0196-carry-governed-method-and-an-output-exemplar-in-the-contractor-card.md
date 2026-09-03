---
title: "Carry governed method and an output exemplar in the contractor card"
status: accepted
category: decisions
created: 2026-09-02
updated: 2026-09-02
tags: [workforce, hiring, card-quality, contract-schema]
related:
  - docs/roadmap/issue-AR-379-hire-schema-has-no-home-for-domain-procedure.md
  - docs/roadmap/issue-AR-380-execution-profile-prose-is-casefolded.md
  - docs/roadmap/issue-AR-235-autonomous-gap-hiring-with-isolated-security-review.md
supersedes: []
superseded_by: null
id: ADR-0196
type: decision
deciders: [owner, maintainers]
---

# ADR-0196: Carry governed method and an output exemplar in the contractor card

## Context

AR-379 asked whether a hired contractor's card should carry domain method —
how to do the work — or only scope: what the specialist is for, its authority,
and the evidence it owes.

Three measurements settled the ground.

**The packaged roster carries no method at all.** All 265 packaged specialist
cards were read. Not one contains an ordered procedure, domain craft, or a
worked output example. They are scope contracts: identity, task types,
capabilities, prefer/avoid, required tools, expected output, required
evidence, audit constraints, provenance. Two adversarial passes tried to find
a counterexample and failed. This is deliberate, not neglect:
`core/roster/semantic_projection.py` renders "only allowlisted reviewed
fields; raw upstream prose is never executable", and every card states that
the upstream definition "is retained only as immutable provenance and is not
included in executable context".

**The contractor card is the only artifact with typed method slots.** Five of
the v2 template's twelve sections come from the execution profile —
`inspect_before_acting`, `working_principles`, `failure_modes_to_check`,
`verification_steps`, `stop_conditions`. The packaged card has zero. The
contractor card is also the only one with a filler gate: `_execution_items`
rejects "follow best practices", "use good judgment" and anything under three
words, so its method slots structurally cannot be padded with generic advice.

**Those slots cannot currently hold real method.** Two ceilings. Every
execution-profile item is casefolded (AR-380), so a principle naming
`America/Chicago` renders `america/chicago`, which is not a valid IANA zone
identifier; the same corruption reaches any code identifier, path, or proper
noun. And each item is capped at 160 characters and rendered as one bullet
among several, so there is no room for a worked output exemplar and nowhere it
would read as an artifact rather than as another maxim.

The generated `host-time-environment-inspector` card is the concrete case: it
names `timezone ambiguity` as a failure mode and never says what to do about
it, and its entire `working_principles` is one sentence.

The closed-profile rule is not in question. A model-authored prose prompt
cannot be checked for whether it declares `external_mutation`, so prose stays
forbidden on both paths.

## Decision

1. **Method is in scope for a contractor card, expressed only through the
   closed schema.** A card may say how to approach its bounded work. It may
   never carry a raw prompt or free prose.
2. **Add `output_exemplar`** as a top-level employment-contract field at
   schema version 3: a single case-preserving string of at most 512
   characters, rendered in its own template section. It shows the shape of a
   finished answer rather than describing it. Like every other contract
   string it is whitespace-collapsed to one line by `_text`, so an exemplar
   is written as a single dense line using inline separators rather than as a
   multi-line mock-up. That is deliberate: a field that preserved newlines
   could forge the template's own section boundaries.
3. **Execution-profile prose keeps its authored case** from v3 (AR-380), and
   `working_principles` carries a structural minimum of two items so a single
   maxim is refused by the parser rather than left to the critic's judgement.
   The
   identifier lists that share `_items` keep casefolding, because normalized
   casing is load-bearing there for matching and dedup.
4. **The prompts require the procedure.** The generator authors an ordered
   decision procedure in `working_principles` that resolves each failure mode
   the card names, plus an exemplar. The hiring critic rejects a single-maxim
   principle set for a role that names failure modes it never answers, and an
   empty exemplar for a role with a procedure.

## Consequences

- `HIRING_CONTRACT_SCHEMA_VERSION` goes 2 to 3 and the contractor prompt
  template goes 2 to 3 with its own computed hash. Versions 1 and 2 stay
  parseable so already-registered workers replay unchanged; only live hiring
  requires the current version.
- Every newly rendered card changes, so `prompt_hash` moves for new hires.
  Workers already registered keep the hashes they were minted with.
- Cards get longer and more specific. The filler gate and the closed schema
  are what keep that from becoming unauditable prose.
- The packaged 265 remain scope-only. This decision does not touch the
  upstream projection policy. If governed method proves out on the contractor
  path, extending it to the packaged roster is a separate decision with its
  own audit and provenance questions.

## Alternatives

- **Leave it as scope-only.** Coherent: Agency is advisory and the executing
  host supplies craft. Rejected because a card is the whole of what Agency
  delivers for a turn; one that carries no method delivers governance alone,
  and the owner's standing position is that even a trivial request has an
  expert who adds something.
- **Procedure only, no exemplar field.** Cheapest, and needs no schema change
  on its own. Rejected as insufficient: the casefold destroys the identifiers
  a procedure must cite, and 160 characters in a list of principles is neither
  long enough for a worked answer nor a place a reader would recognise one.
  Fixing the casefold alone still leaves no case-preserved home for an answer
  shape.
- **Exemplar only, no procedure requirement.** Rejected: an exemplar shows the
  destination and never the route. It would spend the whole version migration
  and still ship cards whose `working_principles` is a single maxim.
- **Allow a raw authored prompt.** Rejected on the standing closed-profile
  grounds: unauditable, undiffable, and uncheckable by the hiring critic.
