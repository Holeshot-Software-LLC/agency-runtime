---
title: "AR-390: The recruiter's cards hide the outcomes that name the unit's work"
status: done
category: roadmap
created: 2026-09-04
updated: 2026-09-04
tags: [workforce, recruiter, critic, staffing, inference]
related:
  - docs/decisions/0206-show-every-outcome-on-the-card.md
  - docs/decisions/0203-show-the-recruiter-the-complete-eligible-card-set-per-unit.md
  - docs/decisions/0205-show-the-critic-the-eligible-neighbourhood-it-judges-against.md
  - docs/roadmap/issue-AR-389-critic-judges-neighbours-it-cannot-see.md
  - docs/roadmap/issue-AR-387-recruiter-cards-carry-no-eligibility.md
  - docs/roadmap/issue-AR-383-inferred-subject-context-fails-its-own-projection.md
  - docs/roadmap/handoffs/issue-AR-383.md
supersedes: []
superseded_by: null
type: issue
epic: reliability
issue_id: AR-390
priority: p1
tracker_url: null
depends_on: []
blocks: []
---

# AR-390: The recruiter's cards hide the outcomes that name the unit's work

## Problem

After ADR-0205 the strict critic's remaining vetoes on the eleven install
wordings each named an eligible card the recruiter had ranked below its
selection. On turns 202 and 205 the recruiter required `evidence-collector`
alone on the install-verification unit and left
`cross-platform-release-verifier` acceptable, scoring them 0.88 and 0.80 on
one turn and 0.88 and 0.78 on the other; the critic vetoed both teams as
wrong-neighbour selections, and it was right.

The recruiter's compact card carries a contract's first two outcomes only.
Every enabled contract on the installed roster declares at least three
(median three, at most `MAX_OUTCOMES`, eight). The release verifier's card
therefore read "evidence-backed release readiness, verified installed-product
portability", while its third and fifth outcomes, "installed-artifact smoke
testing" and "upgrade and uninstall verification", named the unit's work
exactly and never reached the recruiter. The evidence collector's two visible
outcomes, "capture reproducible UI evidence, compare expected and observed
states", read as generic verification and won. The recruiter's judgment
was sound on what it was shown; what it was shown was cut.

The hybrid-recall additions already carry every outcome; only the compact
card the recruiter reads for the bounded recall rows was truncated, and the
critic's neighbourhood card (ADR-0205) copied the same cut.

## Current state

Offline replays of the two captured recruiter calls (raw390, gateway cache
bypassed, three trials each) with every outcome on every detail card: on
turn 202 the release verifier is required in three of three trials against
two of three at baseline; on turn 205 one of three against none of three,
with the recruiter's replies on that turn varying widely in both variants.
The documents grow from 51.6 to 55.2 and from 52.0 to 55.6 kilobytes; every
one of the 65 cards gained at least one outcome. Showing every outcome costs
a median of 42 bytes per card.

Live on the same eleven wordings with every outcome on the cards
(2026-09-04): the release verifier is on the verification unit in 7 of the 8
turns that reached the critic, against 5 of 9 on the ADR-0205 run; completed
4 against 6, with two turns lost to unreadable recruiter replies, one to the
strict call budget after two repairs, and four vetoes that now point at the
review and plan units (test-results-analyzer alone where code-reviewer and
the release verifier were ranked; operations-manager where the site
reliability engineer was ranked). The completion count sits inside the
variance the three runs show (5, 6, 4); the card change decides which card
the recruiter picks when the discriminating outcome is visible, and on the
verification unit it now picks the release verifier.

## Approach

ADR-0206. The compact recruiter card and the critic's neighbourhood card
carry every outcome and every `not_for` line the contract declares; the only
bound is the contract's own (`MAX_OUTCOMES`). Nothing ranks, filters or
staffs; the prompts are unchanged.

## Dependencies

ADR-0203 and ADR-0205 (the same cards). None blocking.

## Acceptance

- [x] The compact recruiter card carries every outcome and every `not_for`
      line of the contract, and a contract with `MAX_OUTCOMES` outcomes shows
      all of them.
- [x] The critic's neighbourhood card carries the same outcomes and `not_for`
      lines.
- [x] A recruiter document built for a roster whose contract declares five
      outcomes shows all five on the detail card, and the critic document
      shows the same five on the neighbourhood card.
- [x] Measured on the same eleven install wordings under strict mode against
      the same reconciled store copy: the verification units' rankings and
      the completed turns are recorded against the ADR-0205 run.

**Verification (2026-09-04).** The record is frozen at `15c404f3`; the
isolated codex verifier returned satisfied on all four criteria on its
second pass (runs `AR-390.1-20260904-99046fe2`, `AR-390.2-20260904-4ab0b1ec`, `AR-390.3-20260904-25596405`, `AR-390.4-20260904-479476df`). The issue is done.
