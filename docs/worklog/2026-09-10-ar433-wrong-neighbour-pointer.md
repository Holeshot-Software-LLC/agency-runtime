---
title: "Make a wrong-neighbour veto name its neighbour"
status: active
category: worklog
created: 2026-09-10
updated: 2026-09-10
tags: [workforce, critic, staffing, receipts, reliability]
related:
  - docs/roadmap/issue-AR-433-name-the-neighbour-a-wrong-neighbour-veto-points-at.md
  - docs/roadmap/issue-AR-434-plan-policy-reads-a-handoff-request-as-a-code-mutation.md
  - docs/decisions/0246-make-a-wrong-neighbour-veto-name-its-neighbour.md
  - docs/roadmap/evidence/AR-433-critic-veto-population-20260910.json
  - docs/roadmap/evidence/AR-433-live-diagnostic-20260910.json
supersedes: []
superseded_by: null
type: worklog
commit: 80e7bf9ceed5db71ba3a527234bbf612f9dbe97a
short: 80e7bf9c
date: 2026-09-10
pr: https://github.com/Holeshot-Software-LLC/agency-runtime/pull/849
related_issues:
  - docs/roadmap/issue-AR-433-name-the-neighbour-a-wrong-neighbour-veto-points-at.md
  - docs/roadmap/issue-AR-434-plan-policy-reads-a-handoff-request-as-a-code-mutation.md
---

# Worklog detail: fix(workforce): make a wrong-neighbour veto name its neighbour

## Purpose

The owner reported recruitment failing "every other call". The immutable
receipts of the observed Codex session show two terminal strict-critic vetoes
on operational requests between two staffed engineering requests, and the
population since 2026-09-08 shows 27 of 30 critic vetoes across five hosts on
`wrong-neighbor-selection` with no receipt able to name the card the critic
preferred. The critic schema carried codes alone, so ADR-0205's "must point at
a card" had nothing to hold it to. This commit makes the claim accountable.

## Approach

`CRITIC_RESPONSE_SCHEMA` gains an optional bounded `wrong_neighbors` pointer
array; the contract and system prompt say a wrong-neighbour code requires it
and that the runtime checks it. The parser verifies each pointer against the
`eligible_neighbourhood` the runtime built for the same document: planned unit,
selected worker, eligible unselected neighbour, team not the whole
neighbourhood. An unnamed or unverifiable claim raises one of three new closed
critic validation codes and takes the existing bounded semantic repair with
critic-specific feedback; if that fails the stage fails as
`workforce_inference_failed`, never a veto and never an approval. A verified
pointer is written to the applied critic attempt's `validation_detail` under a
new prefix and both receipts project it through `project_nomination_failures`
as a four-key per-unit row admitted only in that exact shape.

## Challenges encountered

Fixtures that vetoed with a bare `wrong-neighbor-selection` on a single-card
snapshot could not name a pointer because the selected team was the whole
neighbourhood; they now use a neighbourhood runner with one more eligible card
or a ground that needs no pointer. The AR-416 captured qualified veto keeps
its code and adds the pointer it always implied. Plan and recruiter replies
are cached per request within a process, so a test that drives the same
request twice clears the workforce caches first.

The first live diagnostic attempt built its staffing context from an unproven
capability receipt with no capabilities, which made every contract ineligible
and had the recruiter declare a gap before any critic call; the rerun used the
capability set the live staffed Codex turn recorded. The gateway served cached
planner replies to the control runs, so control and candidate are single
samples under each contract, not a controlled A/B on the critic alone.

## Decisions and alternatives

ADR-0246 records the decision and the rejected alternatives (approve when the
critic cannot name a card; drop the ground; carry identities in reason codes;
add a receipt column). The observed session's second veto also exposed the
plan-policy misclassification of a handoff request as a code mutation, filed
as AR-434 without a repair.

## Verification

Focused critic set 181 passed (`tests/test_critic_wrong_neighbor_pointer.py`
plus the strict-critic, eligibility-view, qualified-reasons, staffing-receipt,
reservation, inference and chaos suites). Named fast Python spine 1151 passed
and 3 skipped; UI 224 passed; docs metadata, policy availability, worklog,
`verify_docs` with and without `--require-tracker`, strict tracker parity
(425 items), Ruff and `git diff --check` passed. Routing eval correctness
gates all passed while two `retrieval_scale` warm-latency gates failed under
concurrent load; clean main also exits non-zero on this machine for the same
area. Six `tests/test_fail_open_disclosure.py` failures pre-exist on clean
main and are unrelated. Decision conformance: 188 of 188 mutations killed, zero survivors, source unchanged. Live
diagnostic: candidate approved 2 of 2 on the critic's first reply; control
vetoed the merge request with a bare unnamed code and approved the handoff
request. No exhaustive or Windows workflow ran.

## Follow-ups

- AR-433 acceptance record and isolated verdicts after merge.
- AR-434 plan-policy repair with the exact wording as a regression.
- The recall reranker reply was invalid in three of four diagnostic runs; it
  is already visible on receipts and remains outside this package.
