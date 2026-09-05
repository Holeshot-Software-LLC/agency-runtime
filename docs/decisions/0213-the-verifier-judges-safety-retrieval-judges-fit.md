---
title: "The verifier judges safety; retrieval judges fit"
status: superseded
category: decisions
created: 2026-09-04
updated: 2026-09-04
tags: [workforce, recruiter, staffing, retrieval, verifier, reliability]
related:
  - docs/decisions/0217-keep-subject-domains-out-of-execution-authority.md
  - docs/roadmap/issue-AR-394-recruiter-teams-fail-or-mis-select.md
  - docs/roadmap/issue-AR-370-staffing-asks-the-wrong-question.md
  - docs/decisions/0211-give-retrieval-a-subject-and-name-the-empty-turn.md
  - docs/decisions/0207-tell-the-recruiter-how-its-ranking-becomes-the-team.md
  - docs/decisions/0198-waive-the-typed-requirements-the-roster-declares-but-cannot-serve.md
  - docs/worklog/README.md
supersedes: []
superseded_by: docs/decisions/0217-keep-subject-domains-out-of-execution-authority.md
id: ADR-0213
type: decision
deciders: [owner]
---

# ADR-0213: The verifier judges safety; retrieval judges fit

## Status

**Accepted 2026-09-04.** Filed as the second half of AR-394, alongside the
shortfall vocabulary that answers its first half.

## Context

Four live `UserPromptSubmit` reproductions on 2026-09-04 ended at the recruiter
stage. The fifth was accepted, and its proposal is the reason this decision
exists. For the ask *"add rate limiting to the public API gateway and write
tests for it"*, `unit-implement-rate-limiting` was staffed with
`roblox-systems-scripter` and `threat-detection-engineer` at confidence 0.9,
margin 0.9, against floors of 0.8 and 0.1. The deterministic verifier accepted
it.

It accepted it correctly. `STAFFING_VERIFIER_REASON_CODES` holds 33 codes and
every one is structural: roster hashes and generations, budget ceilings, set
and ordering equalities, deterministic minimality, typed coverage, eligibility,
and the recruiter's own reported confidence and margin. Not one names
topicality. `selection_confidence_too_low` is the code closest to the
temptation, and it reads the score the recruiter reported *about itself*, so a
confident wrong answer clears it exactly as a confident right one does.

The roster was not short. `api-platform-engineer` sits in it, in division
`engineering`, beside `roblox-systems-scripter` in `game-development`.
Retrieval offered the second and never the first. Every safety property held
over the team the recruiter was handed; the team was simply about the wrong
subject.

## Decision

**The deterministic staffing verifier does not judge topical fit, and will not
be given a term for it.** Its contract is that an accepted team is *safe*:
present, enabled, eligible for this host and platform, covering the unit's
typed requirements, within budget, minimal, and derived from the ranking it
claims. Whether the team is *apt* for the request is decided upstream, by
retrieval, and is AR-370's question.

Two consequences follow, and both are recorded rather than left implicit.

1. **A fit floor is not the fix.** AR-394 already rejected lowering
   `min_confidence` because it converts rejections into acceptances of exactly
   these teams. A fit floor is the same error inverted: it converts
   mis-selection into abstention, and abstention on this machine is already the
   dominant outcome — the recruiter was contract-invalid on 395 of 529 attempts
   in the last 400 receipts. Adding a veto to a stage that mostly vetoes itself
   buys nothing and hides the supply failure underneath it.

2. **The receipt must say when supply is the fault.** A verifier that will not
   judge fit owes the reader an account of who failed to offer a candidate.
   That is what the AR-394 shortfall vocabulary does:
   `coverer_absent_from_retrieval` names a requirement the roster covers
   eligibly and retrieval never surfaced, and separates it from
   `ranked_candidates_ineligible`, where retrieval did surface the specialist
   and deterministic eligibility refused it. The two have opposite fixes, and
   before this they were one receipt shape.

## Consequences

The accepted-but-inapt team stays possible until AR-370 closes. That is
deliberate: the alternative is a turn that abstains rather than one that staffs
imperfectly, and under the staff-first doctrine an advisory workforce that
answers with the wrong specialist is recoverable in a way that an unstaffed
turn is not.

The reranker's contribution is bounded by the same reasoning. Under
`dense_recall_mode: additive` the reranker never reorders candidates; it can
only add a card the typed baseline did not admit, and an empty result returns
the baseline unchanged. Measured on 2026-09-04, `recall_reranker` was
contract-invalid on 29 of 142 attempts and returned no valid response on 4
more, so it contributed nothing on 23.2% of the turns that ran it. The recorded
effect of that degradation is therefore not a worse ordering but a smaller
candidate set — which is `coverer_absent_from_retrieval`, on the receipt, by
name.

## Rejected alternatives

- **A topical-fit floor in the verifier.** Rejected above.
- **Reading fit from the recruiter's confidence.** The number is the model's
  self-report; the accepted turn scored 0.9 on a team about the wrong platform.
- **Rejecting a division mismatch between unit and contract.** Division is a
  roster taxonomy, not a typed requirement, and a unit may legitimately want a
  specialist from a neighbouring division. Encoding it as a safety property
  would make the verifier's contract depend on how the roster happens to be
  filed.
