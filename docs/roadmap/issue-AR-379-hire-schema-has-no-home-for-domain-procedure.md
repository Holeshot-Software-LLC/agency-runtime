---
title: "AR-379: The hire schema has no home for domain procedure, so generated cards are governed but generic"
status: done
category: roadmap
created: 2026-09-02
updated: 2026-09-02
tags: [workforce, hiring, card-quality]
related:
  - docs/roadmap/issue-AR-376-hiring-sends-the-entire-workforce.md
  - docs/roadmap/issue-AR-374-host-capability-vocabulary-gap.md
supersedes: []
superseded_by: null
type: issue
epic: workforce
issue_id: AR-379
priority: p2
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/553
depends_on: [AR-380]
blocks: []
---

# AR-379: The hire schema has no home for domain procedure, so generated cards are governed but generic

## Problem

`_HIRE_SYSTEM` ends:

> Do not write a raw prompt or generic guidance; the runtime compiles the
> closed profile through a fixed reviewed template.

The closed-profile rule is correct and should stay. It is what makes a card
auditable, diffable, provenance-hashed, and reviewable by the hiring critic.
A model-authored prose prompt cannot be checked for whether it declares
`external_mutation`.

The instruction is doing two jobs and only one is load-bearing. Forbidding
unauditable prose is necessary. Forbidding "generic guidance" while the schema
offers nowhere to put a decision procedure produces cards that are well
governed and hollow on domain craft.

## Current state

Hiring was exercised end to end for `what time is it`, a genuine gap: 291
workers with no time specialist. It hired `host-time-environment-inspector`,
"Read-Only Host Time Environment Inspector".

Where the generated card is stronger than a typical hand-written prompt:

- `hard_negative_evaluations` with scenario, expectation and rationale
- `failure_modes_to_check`: clock access unavailable, timezone ambiguity,
  output formatting drift, accidental mutation
- `verification_steps`, `stop_conditions`, `forbidden_scenarios`
- `external_mutation: false`, `evidence_requirements`

Where it is weaker. Compared against a hand-written "Current Time Agent"
prompt supplied by the owner, the card is missing every piece of actual
horology:

| domain content | hand-written | generated card |
|---|---|---|
| ordered timezone resolution (explicit, then session metadata, then ask) | yes | absent |
| daylight saving handling | yes | absent |
| IANA naming guidance | yes | absent |
| concrete output exemplar | yes | absent |
| multi-location and conversion behaviour | yes | absent |

The card *names* `timezone ambiguity` as a failure mode and never says what to
do about it. Its entire `working_principles` is one sentence: "Observe first,
report exactly, and do not invent missing time values."

## Approach

Not decided, and deliberately not "drop the closed profile".

1. Keep the closed schema and require domain specificity inside it:
   `working_principles` carrying an ordered decision procedure rather than a
   single maxim, with the hiring critic rejecting a one-line principle set for
   a role that plainly has procedure.
2. Add a bounded output-exemplar field so "concise factual form" can show
   rather than tell.
3. Leave it, and accept that cards govern scope while the executing host
   supplies domain craft.

Option 3 is coherent and may well be right, since Agency is advisory and the
host does the work. It should be chosen deliberately rather than by omission.

## Dependencies

- Requires hiring to be runnable, which AR-376 and AR-377 currently make
  marginal.

## Acceptance

- [x] The decision is recorded, with an ADR if the closed-profile posture
      changes.
- [x] If specificity is required, a generated card for a procedural role
      carries its ordered procedure, and a regression case pins that a
      single-maxim principle set is rejected for such a role.
