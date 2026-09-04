---
title: "Show every outcome on the card"
status: accepted
category: decisions
created: 2026-09-04
updated: 2026-09-04
tags: [workforce, recruiter, critic, staffing, inference]
related:
  - docs/roadmap/issue-AR-390-recruiter-cards-hide-the-outcomes-that-name-the-work.md
  - docs/decisions/0118-require-inference-owned-staffing.md
  - docs/decisions/0203-show-the-recruiter-the-complete-eligible-card-set-per-unit.md
  - docs/decisions/0205-show-the-critic-the-eligible-neighbourhood-it-judges-against.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
id: ADR-0206
type: decision
deciders: [owner]
---

# ADR-0206: Show every outcome on the card

## Status

**Accepted 2026-09-04.** Item 2 of the AR-383 capsule's next package after
the AR-389 close, filed as AR-390.

## Context

The recruiter ranks candidates from compact cards: identity, outcomes, scope
qualifiers and `not_for` lines. The card carried the contract's first two
outcomes only, a bound chosen for document size when the roster was small.
Every enabled contract on the installed roster now declares at least three
outcomes, and the outcome that names a unit's work is often the third or
later. On 2026-09-04 the cross-platform release verifier's "installed-artifact
smoke testing" and "upgrade and uninstall verification" never reached the
recruiter on two install-verification units; it required the evidence
collector alone from that card's "capture reproducible UI evidence", and the
strict critic, now shown the eligible neighbourhood (ADR-0205), vetoed both
teams correctly. Replaying the recruiter with every outcome on the cards
required the release verifier three times of three.

## Decision

1. **The compact recruiter card carries every outcome and every `not_for`
   line** the contract declares. The only bound is the contract's own
   (`MAX_OUTCOMES`); no card-side truncation remains.
2. **The critic's neighbourhood card carries the same.** The recruiter and
   the critic read the same account of a worker (ADR-0205 already gives them
   the same boundary).
3. **Nothing else changes.** The prompts, the recall bounds, the ranking
   contract and the verifier are untouched; the runtime still selects, ranks
   and staffs nothing (ADR-0118).

## Consequences

- The recruiter document grows by about a kilobyte at the recall bound (a
  median of 42 bytes per card, at most a few hundred); on the captured
  turn-202 document, 51.6 to 55.2 kilobytes.
- A contract's later outcomes now carry weight in ranking, so roster
  curation should keep outcomes ordered by importance but no longer needs to
  front-load the discriminating one.
- Measured live on the eleven wordings (2026-09-04): the release verifier on
  the verification unit in 7 of 8 critic-reached turns against 5 of 9;
  completions 4 against 6 inside a 5, 6, 4 run-to-run spread, with two
  transport losses, one budget exhaustion and four vetoes that moved to the
  review and plan units. The recruiter's fit judgment on those units, and
  the transport's unreadable replies, are what remain.

## Alternatives

- **Raise the cut to three or four.** Rejected: any cut hides some
  contract's discriminating outcome, and the cost of showing all eight is a
  few hundred bytes.
- **Match the unit's tokens against outcomes and show the matching ones.**
  Rejected: that is deterministic ranking of evidence (ADR-0118), and the
  matching would be lexical where the recruiter's judgment is semantic.
