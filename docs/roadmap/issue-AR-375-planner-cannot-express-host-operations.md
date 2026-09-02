---
title: "AR-375: An actionable install is planned as a read-only unit, so the eligible installer specialist is never staffed"
status: wont_do
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

**Closed not reproducible, 2026-09-02.** The behaviour this issue describes was
observed exactly once and did not recur. Kept as a record because the
investigation corrected two other claims, and because the negative result is
worth not rediscovering.

## Problem

As filed: for `install this: https://zcode.z.ai/en` the planner produced three
units — `analysis`, `plan`, `test-evidence` — all read-only. Nothing
represented the work the host would perform, so no executor specialist was
staffed and the critic rejected the staffing with
`missing-installation-executor`, `wrong-routine-installation-staffing` and
`missing-implementation-lifecycle`.

## Current state

That was one sample, and the generalisation drawn from it does not hold.

Re-measured against the same installation and the same request:

| run | host | fresh | plan | executor unit | status |
|---|---|---|---|---|---|
| original | codex | yes | 3 units, all read-only | no | critic rejected |
| A | claude | yes | 5 units | yes | `accepted` |
| B | claude | cached | 5 units | yes | `accepted` |
| C | claude | cached | 5 units | yes | `accepted` |
| D | codex | yes | 5 units | yes | `inference_invalid` |

Every fresh run after the original produced the executor unit. The accepted
runs planned `analysis`, `implementation-change`, `test-code`,
`review-report`, `test-evidence` and staffed seven specialists:
`codebase-onboarding-engineer` for discovery,
`cross-platform-installer-engineer` and `devops-automator` for the
implementation, `software-test-engineer` for tests, `code-reviewer` for
review, and `cross-platform-release-verifier` with `test-results-analyzer`
for evidence.

So the pipeline does staff an install correctly. The single read-only plan was
planner output variance, not a structural defect, and it is not a defect this
issue can characterise from one observation.

Two facts established here are worth keeping:

- **Turn classification does not foreclose an executor.**
  `classify_turn_intent` returns `execution_decision_required=True` for
  `install this: <url>`, so `_workforce_planning_options` applies no
  constraint and the planner is free to choose any artifact kind. The
  planner-versus-classifier question this issue raised is answered: the
  classifier is not involved.
- **Repeat runs are not independent samples.** The plan and recruiter stages
  cache, so runs B and C replayed run A. Measuring how often the planner omits
  an executor needs cache-busting across varied requests, not repetition of
  one.

## Approach

None. Closed without a change.

If the omission is seen again, the thing to measure first is its rate across
distinct operational requests with the cache bypassed. A single occurrence is
not enough to justify touching `_PLANNER_SYSTEM`, whose "Do not invent
implementation, release, or deployment work beyond the request" sentence
exists to prevent the opposite failure.

## Dependencies

- AR-374 cleared the tools axis, which is what let the turn reach the critic
  and made the original observation possible.

## Acceptance

Not applicable; closed not reproducible.

## Unresolved observation

Run D planned correctly and still ended `inference_invalid` /
`workforce_inference_failed` on the codex host. That is a later-stage failure
and is not this issue's subject; it may be the intermittent recruiter provider
failure recorded as a follow-up in AR-374.
