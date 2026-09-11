---
title: "Enforce the reviewer independence the plan calls for at the verifier"
status: accepted
category: decisions
created: 2026-09-10
updated: 2026-09-10
tags: [workforce, staffing, verifier, critic, inference]
related:
  - docs/roadmap/issue-AR-437-enforce-reviewer-independence-the-plan-calls-for.md
  - docs/roadmap/issue-AR-433-name-the-neighbour-a-wrong-neighbour-veto-points-at.md
  - docs/decisions/0213-the-verifier-judges-safety-retrieval-judges-fit.md
  - docs/decisions/0200-bind-the-strict-critic-to-the-advisory-doctrine.md
  - docs/decisions/0118-require-inference-owned-staffing.md
  - docs/roadmap/evidence/AR-433-install-liveness-20260910.json
  - docs/worklog/README.md
supersedes: []
superseded_by: null
id: ADR-0249
type: decision
deciders: [owner]
---

# ADR-0249: Enforce the reviewer independence the plan calls for at the verifier

## Status

**Accepted 2026-09-10.** Owner asked for AR-437 to be filed and repaired the
same way as AR-433.

## Context

The staffing verifier requires independent assurance only for units with
modify authority (`_assurance`), and its review-relation findings fire only on
contracts that declare `must_review_independently`. A plan whose review-report
unit depends on an analysis unit and says "independently review" it therefore
passed the verifier with the same worker on both units. On 2026-09-10 every
captured critic packet for one ordinary-review request had exactly that shape,
with `code-reviewer` on both units and `silent-failure-hunter` and
`type-design-analyzer` ranked and eligible on the review unit. Across the four
host runs the strict critic vetoed that shape twice as
`missing-lifecycle-assurance-the-plan-calls-for` and approved it twice (the
evidence file records packets by capture time, not by host). The verdict was a
coin flip on a requirement the runtime could have checked deterministically
before the critic ever saw the team.

## Decision

1. **The verifier owns it.** `_reviewer_reuse` runs beside `_assurance`: for
   every review-authority unit whose artifact kind and lifecycle phase are
   assurance kinds and whose timing is `after_artifact` (the same predicate
   `_has_assurance` and `_composition` use), any selected worker also selected
   on a unit it reviews (an ancestor in the plan) is a reuse.
2. **Repairable when an independent team exists.** The verifier derives, with
   the same `_minimum_team` machinery and coverage waivers the selection uses,
   a covering team for the review unit from the recruiter's own executable
   ranking with every worker selected on a reviewed unit removed. The
   executable ranking already excludes ineligible and recruiter-forbidden
   candidates, and a lone eligible worker that cannot cover the unit is not a
   team. If such a team exists, the reuse is the fatal finding
   `review_reviewer_reused` naming the review unit, the reused worker and the
   reviewed unit, and the recruiter repair feedback carries those identities
   (`reused_workers`, `reviewed_units`) beside guidance to rank the
   independent workers as required or to restaff the reviewed unit.
3. **Nothing when none does.** If no independent covering team exists the
   verifier adds nothing: the team stays staffable and no existing receipt
   code changes meaning, so gap hiring's per-unit rule and the advisory
   `independent_assurance_missing` (a modify-unit finding) are untouched.
4. **Not changed.** Inference still ranks and selects; the runtime adds no
   worker (ADR-0118). The critic's grounds and contract are unchanged
   (ADR-0200); after this it sees either an independent review or a team that
   provably could not have one. The single explicit indivisible unit stays
   exempt with the rest of assurance.

## Consequences

- The captured shape becomes one recruiter repair instead of a critic coin
  flip. The receipt names the reused worker and the reviewed unit on the
  rejected recruiter attempt, and the repair feedback names them too.
- A team the runtime accepted before is refused only when its own ranking
  holds an independent covering team, so the refusal is always repairable by
  the recruiter; a first draft that decided the branch on per-worker
  eligibility was withdrawn in review because it could refuse a team no repair
  could fix and widened a receipt code onto non-modify units.
- A recruiter that repeats the reuse on its repair fails the stage as
  `workforce_inference_failed` with the same finding; that is the honest
  outcome for a review the plan required and the roster could provide.
- `review_reviewer_reused` joins the verifier's closed vocabulary, so both
  receipts admit it on rejected attempts (ADR-0202).

## Alternatives

- **Leave it to the critic.** Rejected: the critic's verdict on this shape was
  observed to be inconsistent, and the runtime holds every fact needed to
  decide it.
- **Always fatal, even without an alternative.** Rejected: it would unstaff
  turns the roster cannot serve better, against the staff-first doctrine.
- **Advisory `independent_assurance_missing` on the reviewed unit when no
  alternative exists.** Rejected in review: the code is a modify-unit finding
  that gap hiring and both receipts key on, and widening it changed their
  meaning.
- **Have the runtime pick the alternative.** Rejected: selection stays with
  inference (ADR-0118); the verifier names the defect and the recruiter fixes
  it.
