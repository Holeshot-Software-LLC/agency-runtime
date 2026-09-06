---
title: "AR-125 matched evaluation reconciliation handoff"
status: active
category: roadmap
created: 2026-09-05
updated: 2026-09-05
tags: [handoff, evaluation, evidence, backlog]
related:
  - docs/roadmap/issue-AR-125-workforce-and-one-shot-evaluation.md
  - docs/roadmap/AR-404-oldest-first-reconciliation-20260905.md
  - docs/roadmap/AR-119-rule-host-evidence-matrix.md
  - docs/roadmap/issue-AR-178-evaluate-one-shot-applications-post-production.md
  - docs/decisions/0102-defer-one-shot-application-evaluation.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-125
branch: codex/ar125-oldest-first-reconciliation
evidence_commit: bc3922285ca695a8c4638c481d0b3fbb7b8835ae
minimum_ledger_commit: b091a0265f2f49ef6a49661c6a5f457b7344b806
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/138
---

# AR-125 matched evaluation reconciliation handoff

## Checkpoint

Fourth oldest-first disposition under AR-404. AR-125 remains relevant and open;
record reconciliation does not substitute for its live study. The three checked
acceptance items are historical candidate receipts, not a current recertification.

## Completed evidence

At bc392228 the evaluator machinery exists. Local comparison, workforce-selection,
upstream-selection and full-roster tests pass: 33 cases in 2.68s, including
identical controls and malformed-arm invalidation. No provider call or native
host trial ran. Runtime/test/script/workflow source is unchanged.
ADR-0102 already defers complete one-shot applications to AR-178. Its expensive
corpus is not an AR-125 closure gate. All six acceptance states stay unchanged.

## Exact blocker

Configured/held-out matched-selection, paired Agency-on/off outcome lift with
exact-version participation, and all five exact live host proofs remain absent
from the current canonical completion evidence. The matrix labels matched value
unproven. Old candidate 29da6eca Windows/Linux evidence and September deterministic
smoke do not fill those gaps. Current session header evidence is unverified.

## Same-task continuity

Publish the disposition through the owned worktree PR and narrow worklog ledger.
Keep #138 open. At a context checkpoint, commit the smallest safe pair and
continue in the same task. Do not claim success from fixture tests or repeatedly
call a provider with unchanged missing credentials/trust.

## Next bounded work package

Backlog order: merge this record reconciliation then inspect AR-127.
Later live study: freeze source/install/roster/configuration and usable host/
evaluator identities, collect valid configured and held-out selection first,
then paired independently graded outcomes and exact host artifacts. Operator
credential/trust boundaries are explicit holds; Windows remains with the owner.

## Verification

pytest tests/test_workforce_comparison.py tests/test_workforce_selection_eval.py
tests/test_upstream_selection_eval.py tests/test_full_roster_eval.py -q -W error
--tb=short: 33 passed. Run metadata/policy/worklog/strict docs/tracker/diff gates.
The current turn's unchanged fast-spine/UI evidence is not a new live result.

## Constraints

No new live/provider study, hosted workflow dispatch, Windows run, credential
creation or hook-trust action for record reconciliation. Preserve invalid arms
and matched controls. No new duplicate issue, acceptance waiver or one-shot gate.
