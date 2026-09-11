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

1. **One narrow predicate, shared.** `prose_artifact_request(request)` in
   `plan_policy` reads the negated-scope-stripped request in token order and
   is true only when every mutation verb takes a prose artefact (handoff,
   capsule, note, memo, summary, writeup, and their plurals) as its object
   within a few filler tokens, every code noun in the shared vocabulary
   (`CODE_NOUN_TOKENS`, the policy's nouns plus the planner's `async`,
   `codebase`, `patch`) is locative (`code`, `codebase`, `repo`,
   `repository`), and no strong code verb (`build`, `debug`, `fix`,
   `implement`, `optimize`, `refactor`, `repair`, `rewrite`, `remove`)
   appears. The policy and the deterministic planner call it on the same
   text, so both read the same request the same way.
2. **Such a request is documentation work.** The policy requires the
   documentation unit and its review, never implementation or tests; the
   deterministic planner emits the documentation plan. The planner's
   acceptance contract lists the prose artefacts under
   `documentation_mutation` so an inference planner is told the rule too.
3. **Every request that changes code keeps the code shape.** A change verb
   whose object is the code ("update the auth code and add a note", "edit
   the code and leave a note"), a strong code verb, a non-locative code
   object (`api`, `patch`), or no prose artefact keeps the existing
   classification, including the mixed "update the code and the docs" case
   and the README rewrite. The negated-scope handling (AR-415) still runs
   first; "create a handoff; do not modify the code" now plans as
   documentation where the offline oracle used to call it ambiguous.

## Consequences

- The observed wording now plans as documentation plus review on both the
  inference path and the offline oracle, and the policy no longer forces
  lifecycle units the critic must then judge.
- The exemption is token-level and deliberately narrow: a first draft that
  keyed on bag-of-tokens co-occurrence turned "update the auth code and add
  a note" into documentation work and dropped its security review; the
  object-bound form adopted in review keeps every such request a code
  mutation. The planner's acceptance contract states the guard beside the
  artefact list.
- New prose artefacts join `PROSE_ARTIFACT_TOKENS` by decision, not by
  inference.

## Alternatives

- **Grammar-aware classification.** Rejected as out of proportion; the token
  policy is deterministic and testable and the exemption is small.
- **Add `handoff` to `_DOCS` alone.** Rejected: the existing documentation
  rule still refuses any code token other than `repo`/`repository`, so
  "where the code is" would keep the code-mutation reading.
