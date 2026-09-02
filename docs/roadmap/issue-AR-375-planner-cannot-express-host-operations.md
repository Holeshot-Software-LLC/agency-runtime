---
title: "AR-375: The planner ontology cannot express a host operation, so an install request plans no executor"
status: open
category: roadmap
created: 2026-09-02
updated: 2026-09-02
tags: [workforce, planning, ontology, staffing]
related:
  - docs/roadmap/issue-AR-374-host-capability-vocabulary-gap.md
  - docs/roadmap/issue-AR-336-requalify-the-recruiter-route-for-ordinary-tasks.md
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

# AR-375: The planner ontology cannot express a host operation, so an install request plans no executor

## Problem

With AR-374's tools axis cleared, an ordinary install request reaches the
critic, which rejects the staffing with `missing-installation-executor`,
`wrong-routine-installation-staffing` and `missing-implementation-lifecycle`.
Those are model-authored codes, not constants in the tree.

The planner is not at fault. In the production compact-intent path the
planner authors only `unit_id`, `outcome`, `artifact_kind`, `domains`,
`stacks`, `capability_ids`, `novel_capability` and `depends_on`
(`_COMPACT_UNIT_SCHEMA`). Everything that decides what a unit may *do* —
`authority`, `mutation_scope`, `lifecycle_phase` and `required_tools` — is
derived from `artifact_kind` by `_ARTIFACT_FACTS` and `_required_tools` in
`core/workforce/intent.py`.

Measured against that table:

| artifact kind | lifecycle | authority | mutation | derived required_tools |
|---|---|---|---|---|
| `analysis` | discovery | advise | read_only | repository-read |
| `architecture-record` | design | plan | read_only | repository-read |
| `documentation` | documentation | modify | workspace_write | repository-read, repository-write |
| `implementation-change` | implementation | modify | workspace_write | repository-read, repository-write, code-execution |
| `plan` | planning | plan | read_only | repository-read |
| `review-report` | review | review | read_only | repository-read |
| `test-code` | testing | modify | workspace_write | repository-read, repository-write, code-execution, test-execution |
| `test-evidence` | testing | review | read_only | repository-read, test-execution |

Three of the eight grant `modify`, and **all three are `workspace_write`**.
No artifact kind expresses an operation on the host — installing software,
deploying, configuring, changing system state.

So for `install this: https://zcode.z.ai/en` the planner's only honest
options are:

- `plan` — read_only, no executor. This is what it chose, and the critic
  correctly observed nothing performs the install.
- `implementation-change` — asserts a workspace/repository change that an
  install is not, scoped `workspace_write`, carrying an
  `implementation-complete` claim.

Neither is right, so the turn cannot succeed however good the plan.

## Current state

Measured 2026-09-02 against the shipped index and the bundled ontology.

**`external_write` is unreachable.** It exists in the legacy
`PLAN_RESPONSE_SCHEMA` enum (`external_write`, `read_only`,
`workspace_write`), but no entry in `_ARTIFACT_FACTS` maps to it and
`mutation_scope` is derived, never authored. The reachable set is exactly
`{read_only, workspace_write}`. Consequently
`plan_external_write_requires_separate_authorization` in
`core/workforce/plan_policy.py` cannot fire from the compact path.

That dead policy is the most informative evidence in this issue. Someone
deliberately decided an external write requires separate authorization. The
ontology then made external writes unexpressible, which enforces that
decision absolutely — at the cost of making an install request fail
confusingly rather than declining it clearly.

**The roster is not the constraint.** 87 of 291 workers declare
`implementation-change`, so an executor unit would staff if one could be
planned. Nine declared artifact kinds sit outside the planner ontology
entirely (`evidence-checklist` 4, `validation-notes` 3,
`redaction-findings-log`, `memory-assessment-report`, `evidence-notes`,
`retention-recommendation`, `memory-update-plan`,
`governed-no-op-confirmation`); the planner can never request them. That is
a separate smell, recorded here only so it is not lost.

## Approach

Not decided. Whether Agency should perform host operations at all is a
governance question, and the three answers need different work:

1. **Decline the request clearly.** Recognise an operational request the
   ontology cannot express and abstain with an explicit reason, instead of
   planning a unit the critic then rejects with model-authored codes.
   Smallest change, honours the existing external-write policy, and admits
   Agency does not install software.
2. **Add an operational artifact kind** mapping to (`operations`, `modify`,
   `external_write`). This alone makes things worse: no roster worker
   declares such a kind, so `artifact:<new>` is uncovered for all 291 and the
   unit becomes unstaffable. It requires roster enrichment *and* revisiting
   `plan_external_write_requires_separate_authorization`, which currently
   refuses exactly this.
3. **Treat installs as `implementation-change`.** Cheapest, and wrong: it
   misstates the blast radius as `workspace_write` and attaches an
   `implementation-complete` claim to work that changed no repository.

Recommendation is (1) unless the owner wants Agency executing host
operations, in which case (2) is the honest but much larger path.

## Dependencies

- AR-374 cleared the tools axis, which is what let the turn reach the critic
  and made this visible.

## Acceptance

- [ ] The decision on whether Agency may perform host operations is recorded,
      with an ADR if it changes the external-write posture.
- [ ] An ordinary install request either staffs an executor or is declined
      with an explicit, deterministic reason that names the ontology limit
      rather than surfacing model-authored critic codes.
- [ ] Whichever way it falls, a regression test pins that the reachable
      mutation scopes and the artifact-kind table cannot drift apart from the
      policy that governs them.
