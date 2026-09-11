---
title: "Read a prose-artefact request that only locates the code as documentation work"
status: accepted
category: decisions
created: 2026-09-10
updated: 2026-09-10
tags: [workforce, planner, plan-policy, inference]
related:
  - docs/roadmap/issue-AR-434-plan-policy-reads-a-handoff-request-as-a-code-mutation.md
  - docs/roadmap/issue-AR-415-respect-negated-change-requests.md
  - docs/roadmap/issue-AR-433-name-the-neighbour-a-wrong-neighbour-veto-points-at.md
  - docs/decisions/0200-bind-the-strict-critic-to-the-advisory-doctrine.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
id: ADR-0250
type: decision
deciders: [owner]
---

# ADR-0250: Read a prose-artefact request that only locates the code as documentation work

## Status

**Accepted 2026-09-10.** Owner asked for AR-434 to be filed and repaired the
same way as AR-433 and AR-437.

## Context

`plan_policy_violations` classifies a request as a code mutation from tokens:
a mutation verb beside a code noun, unless a documentation noun is present
and no code noun other than `repo`/`repository` is. The deterministic
planner applies the same shape. "can you create a handoff ... where the code
is and what branch" therefore read as a code mutation (`create` plus
`code`): the policy demanded implementation, test and test-evidence units, the
planner supplied them on repair, and the strict critic vetoed the resulting
team for lacking the lifecycle assurance those units implied. The request
asked for a document that says where the code lives.

## Decision

1. **One narrow predicate, shared.** `prose_artifact_request(tokens,
   code_tokens)` in `plan_policy` is true when a mutation verb appears, a
   prose artefact is named (handoff, capsule, note, memo, summary, writeup,
   and their plurals), every code token the caller found is locative
   (`code`, `codebase`, `repo`, `repository`), and no strong code verb
   (`build`, `debug`, `fix`, `implement`, `optimize`, `refactor`, `repair`,
   `rewrite`, `remove`) appears. The policy passes its own code hits; the
   deterministic planner passes its hits plus a language or framework
   detection, so both read the same request the same way.
2. **Such a request is documentation work.** The policy requires the
   documentation unit and its review, never implementation or tests; the
   deterministic planner emits the documentation plan. The planner's
   acceptance contract lists the prose artefacts under
   `documentation_mutation` so an inference planner is told the rule too.
3. **Everything else is unchanged.** A strong code verb, a non-locative code
   object (`api`, `service`, a language), or no prose artefact keeps the
   existing classification, including the mixed "update the code and the
   docs" case, the README rewrite, and the negated-scope handling (AR-415)
   which still runs first.

## Consequences

- The observed wording now plans as documentation plus review on both the
  inference path and the offline oracle, and the policy no longer forces
  lifecycle units the critic must then judge.
- The exemption is token-level and deliberately narrow; "edit the code and
  leave a note" still reads as a code mutation because `edit` is not a strong
  verb only when the code token is locative and a prose artefact is named,
  and here the artefact is named, so it reads as documentation. That
  ambiguity is accepted: the request names the artefact it wants.
- New prose artefacts join `PROSE_ARTIFACT_TOKENS` by decision, not by
  inference.

## Alternatives

- **Grammar-aware classification.** Rejected as out of proportion; the token
  policy is deterministic and testable and the exemption is small.
- **Add `handoff` to `_DOCS` alone.** Rejected: the existing documentation
  rule still refuses any code token other than `repo`/`repository`, so
  "where the code is" would keep the code-mutation reading.
