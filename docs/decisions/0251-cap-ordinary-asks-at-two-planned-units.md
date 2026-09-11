---
title: "Cap ordinary asks at two planned units"
status: accepted
category: decisions
created: 2026-09-11
updated: 2026-09-11
tags: [workforce, planner, plan-policy, inference]
related:
  - docs/roadmap/issue-AR-441-the-recruiter-answers-a-whole-expanded-plan-in-one-call.md
  - docs/roadmap/issue-AR-438-cap-ordinary-asks-at-two-units.md
  - docs/decisions/0250-read-a-prose-artefact-request-as-documentation-work.md
  - docs/decisions/0249-enforce-the-reviewer-independence-the-plan-calls-for.md
  - docs/decisions/0118-require-inference-owned-staffing.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
id: ADR-0251
type: decision
deciders: [owner]
---

# ADR-0251: Cap ordinary asks at two planned units

## Status

**Accepted 2026-09-11.** Owner direction: strict staffing must work, no
fallback may hide a failure, and an ordinary ask should be one or two units.

## Context

The planner is free to split any request into up to the configured unit
limit, and it does: 33 of 88 completed plans since 2026-09-08 had three to
ten units, and a one-paragraph review request drew two to four. The recruiter
then answers one prompt for all units, 56 KB for two and 91 KB for six, and
its most frequent failure is omitting units (`missing_work_unit`, 57 rows,
none truncated). The coverage gate compounds it: more units means more typed
requirements to cover, and the forced complements are what the strict critic
rightly vetoes. The plan policy already knows which requests genuinely need
a larger shape, because it is the policy that demands those units.

## Decision

1. **The policy decides the ceiling.** `request_profile` exposes the exact
   classification `plan_policy_violations` applies; `planning_unit_ceiling`
   returns two units unless the profile is shape-expanding (a code mutation,
   a security code review, a repository mapping, or regulated assurance) or
   a change verb stands beside a code noun, in which cases the existing
   limits apply. Documentation work, installs with verification, merges,
   questions and reviews fit in two.
2. **The pipeline passes it to the planner** as `max_planned_units`, after
   the activation-canary and contextual-inquiry contracts, which keep
   precedence. Explicit indivisible requests still plan one unit.
3. **Nothing else changes.** Inference still authors the plan within the
   ceiling; the recruiter, verifier and critic are unchanged; no plan is
   accepted that the policy would otherwise refuse.

## Consequences

- The ordinary path becomes a one- or two-unit staffing problem, which is
  where the recruiter succeeds today.
- A request that genuinely needs more units keeps its shape; the recruiter's
  omissions on those plans are the next package (batching the recruiter call
  by unit), not this one.
- The ceiling is a token-level judgement of the request. A wording the policy
  reads as shape-expanding keeps the larger shape. A wording it under-reads
  keeps the planner free only when a change verb (the policy's own or a
  broader list it does not enforce) stands beside a code noun; an under-read
  wording with neither is capped, and a review of the first draft accepted
  that trade because the policy demands nothing of such a plan and the
  planner still chooses its two units.

## Alternatives

- **Lower the configured unit limit globally.** Rejected: it would starve the
  shapes the policy itself demands (four unit kinds for a code mutation).
- **Ask the planner to be frugal.** Rejected: the planner already receives
  that guidance and still splits ordinary reviews into two to four units.
