---
title: "Tell the recruiter how its ranking becomes the team"
status: accepted
category: decisions
created: 2026-09-04
updated: 2026-09-04
tags: [workforce, recruiter, staffing, inference, verifier]
related:
  - docs/roadmap/issue-AR-391-recruiter-prompt-misstates-how-its-ranking-becomes-the-team.md
  - docs/decisions/0118-require-inference-owned-staffing.md
  - docs/decisions/0203-show-the-recruiter-the-complete-eligible-card-set-per-unit.md
  - docs/decisions/0206-show-every-outcome-on-the-card.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
id: ADR-0207
type: decision
deciders: [owner]
---

# ADR-0207: Tell the recruiter how its ranking becomes the team

## Status

**Accepted 2026-09-04.** Item 2 of the AR-383 capsule's next package after
the AR-390 close, filed as AR-391.

## Context

The recruiter classifies each ranked candidate required, acceptable or
forbidden and the runtime derives the team: every required candidate, plus
acceptable candidates only when a typed requirement is still uncovered, the
fewest of them in rank order. The ranking is read as order alone, rank one
scoring 1.0 and each later rank one step lower, and a unit's confidence is
the rank score of its lowest-ranked selected worker, coverage complements
included. The prompt told the recruiter that an acceptable candidate was one
"the runtime may add when needed" and not to "label every strong candidate
required"; it named no score rule and no confidence rule, and a whole-team
rejection came back as a bare code.

On the eleven install wordings (2026-09-04) the review units carried one
requirement, `capability:risk-analysis`, that exactly one eligible card
covered, and that card did not fit the unit. The recruiter ranked the
faithful owner first and that card fourth or fifth, or left it unranked; the
runtime added it as a coverage complement, took the unit's confidence from
its rank, and rejected the team. The repair, told only the code, made the
coverer required and the owner acceptable, the coverer was selected alone,
and the strict critic vetoed the team correctly. Offline, four of six
cache-bypassed replies died that way and one had no safe team.

## Decision

1. **The contract carries the derivation with the verifier's numbers.** The
   recruiter document's `response_contract` states
   `acceptable_candidates_join_only_for_typed_coverage`,
   `ranking_is_read_as_order_only`, `rank_score_step`,
   `confidence_is_the_lowest_selected_rank_score`,
   `margin_is_against_the_best_alternative_team`, `minimum_confidence` and
   `minimum_margin`. The step comes from the one function the scorer uses
   (`_rank_score_step`) and the minimums from the configuration the verifier
   applies, so the account and the rule cannot drift apart.
2. **Each typed recall row names the sole eligible coverers.** For every
   requirement exactly one eligible detail card covers, the row's
   `sole_eligible_coverers` names it. It is the verifier's own eligibility
   and coverage over the cards (the ADR-0203 helper), a fact and not a
   ranking: that card is on every safe team for the unit.
3. **Both prompts state the derivation.** Required is the team; an
   acceptable candidate joins only as a typed-coverage complement in rank
   order and never for fit; the ranking is read as order alone; confidence is
   the lowest selected rank score; rank in team order, with a sole coverer
   directly after the team it completes even when a better-fitting owner
   leads. "Do not label every strong candidate required" is replaced by
   "Required is the team, not an emphasis label".
4. **A whole-team rejection hands back the derived team.** The
   `_StaffingVerificationError` feedback carries, per violated unit, a
   correction sentence for the codes the recruiter can act on
   (`selection_confidence_too_low`, `selection_margin_too_low`,
   `no_safe_sufficient_team`, `unit_agent_budget_exceeded`,
   `selected_agent_budget_exceeded`) and the derived team: selected,
   required, the workers the runtime added for typed coverage, confidence,
   margin and the lowest-ranked selected worker with its rank and rank score,
   plus the thresholds. Identities are roster identities the proposal already
   validated; no request or model content. Codes outside the map stay bare.
5. **The account of fit names `not_for`.** A card whose `not_for` line names
   the unit's work is not a faithful owner however well its name or domain
   matches.
6. **Nothing else changes.** The verifier, the scorer, the selection
   derivation and the critic are untouched; the runtime still selects, ranks
   and staffs nothing (ADR-0118).

## Consequences

- The recruiter document grows by about three hundred bytes (seven contract
  keys and one small mapping per unit); the repair prompt by the derived
  team of each violated unit.
- The recruiter is asked to rank in team order, so a coverage complement may
  sit above a better-fitting substitute. The ranking's consumers in the
  runtime are the team derivation, the confidence and margin, and the
  runner-up list; none reads it as a fit ordering.
- At the installed thresholds (step 0.1, minimum confidence 0.8) a team is
  at most three ranks deep, whatever `maximum_selected_per_unit` says. That
  is operator configuration (`agency.yaml`), now visible to the recruiter as
  numbers rather than discovered as rejections.
- Offline, with the prompt account alone: the 203 replies pass the verifier
  in three of three trials against one of three at baseline; the 209 replies
  still fail in three of three because the sole coverer was left unranked or
  at rank five, which is what decision 2 states outright. The measurements
  with decision 2 and the live eleven-wording run are in the AR-391 evidence
  file.
- The plan-unit loss (305: `operations-manager` required in six of six
  trials against its own `not_for` line, the critic preferring the site
  reliability engineer) is not moved by decision 5 and is recorded on the
  issue as a roster-fit question for plan-authority host-side units.

## Alternatives

- **Take a unit's confidence over the required members only, leaving a
  runtime-added complement out of it.** Rejected: it changes a hard check the
  critic and the receipts rely on, and it would let a team the recruiter
  never looked at past the rank it earned. The recruiter is the selection
  authority; the honest fix is to tell it the rule.
- **Add the best-ranked acceptable card to the team for fit.** Rejected:
  deterministic selection over the recruiter's ranking (ADR-0118).
- **Waive a requirement only one card covers, as ADR-0198 waives one no card
  covers.** Rejected: a served requirement is not a roster gap; the roster
  answers it, poorly or not, and the critic judges the answer.
- **Exempt from the wrong-neighbour veto a selected worker no safe team can
  omit.** Not taken here. Whether the critic vetoes a team that holds both
  the faithful owner and the sole coverer is measured in the live run; if it
  does, that is the critic's account to fix under its own decision.
