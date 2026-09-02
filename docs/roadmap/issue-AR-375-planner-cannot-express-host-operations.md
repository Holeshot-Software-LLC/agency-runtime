---
title: "AR-375: An actionable install is planned as a read-only unit, so the eligible installer specialist is never staffed"
status: open
category: roadmap
created: 2026-09-02
updated: 2026-09-02
tags: [workforce, planning, staffing]
related:
  - docs/roadmap/issue-AR-374-host-capability-vocabulary-gap.md
  - docs/roadmap/issue-AR-336-requalify-the-recruiter-route-for-ordinary-tasks.md
  - docs/decisions/0110-remove-agency-owned-windows-hello.md
supersedes: []
superseded_by: null
type: issue
epic: reliability
issue_id: AR-375
priority: p1
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/545
depends_on: []
blocks: []
---

# AR-375: An actionable install is planned as a read-only unit, so the eligible installer specialist is never staffed

## Problem

With AR-374's tools axis cleared, an ordinary install request reaches the
critic, which rejects the staffing with `missing-installation-executor`,
`wrong-routine-installation-staffing` and `missing-implementation-lifecycle`.
The critic is right.

For `install this: https://zcode.z.ai/en` the planner produced three units:

| unit | artifact kind | authority |
|---|---|---|
| `unit-install-discovery` | `analysis` | advise |
| `unit-install-operation` | `plan` | plan |
| `unit-install-verification` | `test-evidence` | review |

Every one is read-only. Nothing represents the work the host would actually
perform, so no specialist is staffed to guide it.

The roster is ready and waiting. `cross-platform-installer-engineer` is
enabled on all five hosts, declares `modify` authority, sits in the
`implementation` and `release` lifecycle phases, and needs only
`package-management`, `repository-read` and `shell-execution` — all inside
the nine capabilities every host proves. It cannot be reached because a
contract only covers a unit whose `artifact_kind` is among the contract's
declared kinds, and this specialist declares exactly one:
`implementation-change`. A `plan` unit can never match it.

So the defect is the plan's shape, not the ontology and not eligibility.
`implementation-change` is how this roster expresses install work; the
planner simply did not choose it.

## Current state

**Agency is advisory and never executes.** The README states it "does not
execute specialists" (README.md:1063), ADR-0110 describes Agency Runtime as
"primarily an advisory plugin integration", and ADR-0107 records that
"Agency never executes either step" for install commands. The host performs
the work; Agency supplies the expertise the host applies.

That is why a unit's `artifact_kind` and derived `mutation_scope` describe
the work the **host** will carry out under staffed expertise, not something
Agency performs. An earlier revision of this issue argued that the
artifact-kind table could not express a host operation and asked whether
Agency should be allowed to perform one. That framing was wrong and is
retracted: the question does not arise, and `implementation-change` already
carries exactly this meaning — the installer specialist declares it.

The derivation facts remain accurate and are worth keeping, because they
explain why the planner's single choice decides everything: in the compact
intent path the planner authors only `unit_id`, `outcome`, `artifact_kind`,
`domains`, `stacks`, `capability_ids`, `novel_capability` and `depends_on`.
`authority`, `mutation_scope`, `lifecycle_phase` and `required_tools` all
follow from `artifact_kind` through `_ARTIFACT_FACTS` and `_required_tools`.
Choosing `plan` instead of `implementation-change` therefore removes the
authority, the lifecycle phase and the specialist match in one step.

**The reproduction is not the full production path.** The AR-374 capsule's
script calls `plan_and_staff_workforce` directly with `turn_routing_context={}`,
which bypasses `selector.pipeline._workforce_planning_options`. That function
constrains the planner for special turn contracts — a turn whose
classification has `execution_decision_required` false is forced to exactly
one `analysis` unit. Whether a real install turn is additionally constrained
that way is unverified, and it must be established before any planner change,
because the two causes need different fixes:

- If the planner is unconstrained and still chooses `plan`, the fix is
  planner guidance.
- If classification forces a single `analysis` unit, the fix is in the
  classifier and no planner change would help.

## Approach

Not decided; the disambiguation above comes first.

If it is planner guidance, the candidate is `_PLANNER_SYSTEM`'s "Do not
invent implementation, release, or deployment work beyond the request",
which is meant to stop the planner inflating a read-only request into
delivery work. For a request whose entire content *is* an operation, that
sentence may be suppressing the one unit the request needs. Any change here
must not reintroduce the inflation it was written to prevent, so it needs a
regression case in both directions.

## Dependencies

- AR-374 cleared the tools axis, which is what let the turn reach the critic
  and made this visible.

## Acceptance

- [ ] It is established, on the full pipeline path, whether the planner is
      free to choose `implementation-change` for an actionable install and
      declines to, or whether turn classification forecloses it.
- [ ] An ordinary install request produces a unit the installer specialist
      can cover, and that specialist is staffed, with a live receipt.
- [ ] A regression case pins both directions: an actionable operation gets an
      executor unit, and a read-only request is not inflated into one.
