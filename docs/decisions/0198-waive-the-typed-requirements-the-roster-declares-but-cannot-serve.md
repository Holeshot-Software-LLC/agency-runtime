---
title: "Waive the typed requirements the roster declares but cannot serve"
status: accepted
category: decisions
created: 2026-09-03
updated: 2026-09-03
tags: [staffing, workforce, recruiter, verifier, receipts]
related:
  - docs/roadmap/issue-AR-384-staff-decisions-die-on-uncoverable-typed-requirements.md
  - docs/roadmap/issue-AR-383-inferred-subject-context-fails-its-own-projection.md
  - docs/roadmap/issue-AR-373-recruiter-evidence-vocabulary.md
  - docs/roadmap/issue-AR-374-host-capability-vocabulary-gap.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
id: ADR-0198
type: decision
deciders: [owner]
---

# ADR-0198: Waive the typed requirements the roster declares but cannot serve

## Status

**Accepted 2026-09-03.** The owner delegated the AR-384 approach decision with
option 1 (advisory roster-wide coverage gaps, conjunctive rule kept for
coverable tokens) as the recommendation. This record is what was implemented:
option 1 with the two amendments the offline replay and the existing safety
doctrine forced, both stated below.

## Context

The staffing verifier proves a team sufficient only when the union of its
typed coverage contains every requirement token of the unit, conjunctively
across six axes. The planner chooses those tokens from the roster's declared
vocabulary, not from what the roster can cover for the unit's authority and
host. On the 2026-09-03 forty-five-turn preflight smoke, 31 of 48 rejected
recruiter attempts carried `staff_without_safe_team`, 40 of 44 per-unit
entries on the `domain` axis, and in the captured instance no answer the
recruiter could give would have validated: `unit-install-operation` (plan
authority, domains `desktop` and `operations`) named `domain:desktop`, the only
contract declaring that domain carries modify authority, and the roster has no
untyped contract left to wildcard the gap. The prompt told the recruiter that
`uncovered_requirements` never mandates a gap; the validator enforced the
opposite sentence of the same prompt.

Two findings during implementation shaped the decision:

1. **Waiving `domain:desktop` alone does not rescue the captured turn.**
   Replaying the exact recruiter reply through the amended verifier against the
   installed 291-contract roster still rejected the unit, now on the
   `capability` axis: `capability:operations` was covered eligibly by exactly
   one contract, `incident-response-commander`, which the recruiter had rightly
   not ranked for an editor install. `_operations_rule` read only the
   `coordination` and `release` lifecycle phases and never the audited
   `operations` domain that `operations-manager`,
   `sre-site-reliability-engineer` and `it-service-manager` all declare. The
   rule predates domain enrichment.
2. **A blanket waiver of every uncovered token breaks a standing doctrine.**
   `test_named_regulated_assurance_requires_explicit_contract_coverage` pins
   that a unit naming `regulated-assurance-do-178c` with only a generic
   reviewer must abstain, so hiring receives the gap. A token no contract
   declares is a missing specialty, not an unserved one, and the planner's
   `novel_capability` path exists precisely to declare such work.

## Decision

Requirement tokens fall into three classes per unit, computed once by
`typed_staffing_coverage_gaps` over the enabled typed roster with wildcards
excluded. This is the same rule the recruiter already sees as
`typed_recall.uncovered_requirements`, so the prompt and the verifier can no
longer disagree about it.

1. **Covered by some eligible contract: mandatory.** The conjunctive rule is
   unchanged. A ranking that omits or forbids an available complement still
   fails `staff_without_safe_team`, and the repair names the axis.
2. **Declared by some enabled typed contract, covered by none eligibly for this
   unit: waived.** The team search in `_minimum_team` and
   `_minimum_team_with_required` drops the token. The verifier records one
   `roster_coverage_gap` reason per token, with the exact token as its detail,
   on the decision whether it is accepted or not. The code is advisory: it
   rides on accepted decisions like `independent_assurance_missing`, and the
   inferred-gap and hireable-gap filters admit it, because it is the honest
   reason a gap is real rather than verifier dirt.
3. **Declared by no enabled typed contract: mandatory.** A `staff` decision on
   such a unit cannot validate, exactly as before, and the honest answer is a
   gap for hiring.

Supporting changes:

- `typed_recall` rows carry `waived_requirements`. The recruiter and repair
  prompts say waived tokens are never held against the team and that an
  uncovered token outside that set needs a gap unless an untyped candidate
  faithfully fits. The repair contract lists `roster_uncovered_requirement_ids`
  separately and never asks for a complement that cannot exist; the failure
  axis skips waived tokens.
- `_operations_rule` also admits a contract whose declared domain is
  `operations`. This is the code-side form of the issue's option 3 for the one
  scarce token the measurement named; generalising the domain reading to every
  broad capability is a follow-up that needs its own measurement.
- Not done, by design: reinstating wildcard coverage, weakening eligibility,
  or waiving unknown tokens. Eligibility already binds authority, at least one
  shared domain, at least one supported capability, host, platform, tools and
  `not_for`, so a waiver can only ever touch a second domain, capability or
  stack value, or the artifact and lifecycle tokens.

## Consequences

- The captured helix reply now validates: `unit-install-operation` selects
  `operations-manager`, the decision is accepted, and it carries one
  `roster_coverage_gap` for `domain:desktop`.
- Routing receipts show `roster_coverage_gap` in the unit's `reason_codes`
  and the waived tokens themselves as the unit's `coverage_gaps`, at most four,
  admitted only in the closed `axis:identifier` form. A waived token is by
  construction an identifier some audited contract declares, so it is roster
  vocabulary rather than model prose; anything else is dropped.
- A `gap` decision on a unit whose only uncovered tokens are waived, with an
  executable faithful candidate ranked, now reads `gap_with_safe_team` and is
  asked to staff. The roster could not have served the waived token anyway,
  and the prompt already says a gap must not leave a faithful candidate
  behind.
- One extra roster pass per unit at three points: 10 ms for a three-unit plan
  over 291 contracts, `typed_recall` 21 ms, measured on the installed roster.
  No cache was added.
- Hiring keeps its own strict rule: a contractor hired for a gap must cover
  every requirement of the causing unit, waived tokens included.
- Measured live on nine fresh install-flavoured turns (2026-09-03, strict
  mode): the verifier accepted the install unit in four, every one carrying
  `roster_coverage_gap` advisories, and the strict critic vetoed all four. No
  verifier rejection named a waived token. The remaining domain-axis
  failures, three turns, all name `domain:platform`, a coverable token whose only eligible
  coverer is `api-platform-engineer`: the planner's platform (the operating
  system) and the roster's platform domain (API platforms) collide, which is
  the issue's option 2 territory and is recorded there as residue.
- A unit whose required pick is ineligible can now be staffed from its
  acceptable set alone once the unserved tokens are waived; the strict critic
  caught one such wrong neighbour (`api-platform-engineer` on a helix install
  unit). The critic's own behaviour on these turns is filed as AR-386.

## Alternatives

- **Option 2, constrain the planner to coverable combinations.** Larger, and it
  moves the failure to the planner stage instead of removing it. Not chosen.
- **Option 3 as roster work only.** Enriching `operations` onto the operations
  planners fixes this roster and this token; the next scarce token
  (`coordination` 4 contracts, `threat-modeling` 4, `test-code` 3) dies the
  same way. The verifier-side reading of the operations domain is kept
  minimal for the same reason: one measured token, one rule.
- **Pure option 1, waive every uncovered token.** Rejected: it staffs a generic
  reviewer for a named regulated specialty and takes that gap away from
  hiring.
- **Sufficiency over the ranked set only.** Would have reached the helix turn
  without touching the operations rule, but one lazily ranked candidate would
  make every complement advisory, and every partial-ranking gap would flip to
  `gap_with_safe_team`. Rejected for blast radius.
