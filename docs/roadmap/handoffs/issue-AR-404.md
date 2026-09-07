---
title: "AR-404 oldest-first backlog completion handoff"
status: active
category: roadmap
created: 2026-09-05
updated: 2026-09-07
tags: [handoff, backlog, acceptance, delivery]
related:
  - docs/roadmap/issue-AR-173-correlate-route-lab-observations.md
  - docs/roadmap/acceptance/evidence/AR-173-route-lab-correlation-20260907.md
  - docs/decisions/0231-separate-route-lab-correlation-from-turn-persistence.md
  - docs/roadmap/issue-AR-170-fail-dashboard-response-correlation-closed.md
  - docs/roadmap/issue-AR-404-evidence-led-backlog-completion.md
  - docs/roadmap/AR-404-oldest-first-reconciliation-20260905.md
  - docs/roadmap/issue-AR-176-align-full-gate-contract-fixtures.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-404
branch: codex/ar173-oldest-first-reconciliation
evidence_commit: 6afcbcb523d55f4beb2339f2fa5b06c9ecae8a01
minimum_ledger_commit: 6afcbcb523d55f4beb2339f2fa5b06c9ecae8a01
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/672
---

# AR-404 oldest-first backlog completion handoff

## Checkpoint

Owner continues one oldest record, one PR, normal merge, then next. Native
Windows remains with the owner. PR #721 merged accepted AR-172 at 47d40fec,
13:11:01Z September 7. Main was clean and fast-forwarded before the separate
AR-173 tree; 6afcbcb5 records that merge and is the prior clean checkpoint.

## Completed evidence

AR-173 already attaches its trace before explanation. The direct HTTP regression
claimed by the issue is missing, and its durable-routing narrative is wrong:
explanations are diagnostic-only since e5f4a8c2, before the issue was written.

- New real HTTP test executes two social explanations, prohibits inference,
  and checks UUID freshness, attachment before explanation, exact response/log
  digest equality, bounded metadata and no task/session/bearer/prompt leakage.
- No turn or routing-decision rows are created. Invalid and disabled calls
  cannot allocate a routing trace; disabled mode still bypasses host/catalog.
- Two focused HTTP tests pass; exact raw stdout is in the receipt.
- No production change. ADR-0231 reconciles criteria 1/4/5 with existing bypass,
  diagnostic-only routing and bounded verification. Originals remain.
- Broader checks and isolated acceptance are pending. Do not mark done.
- AR-172 done leaves 40 actual trackers plus 82 legacy, 122 unfinished.

## Exact blocker

No reproduced AR-173 production defect. Finish focused-to-spine verification
and an immutable complete five-criterion evidence packet before isolated review.
The below-50-percent checkpoint commits this safe regression/record slice,
then continues the same task.

AR-170 remains in_progress: first review at 662eb947 and final candidate
91273e41 are preserved. Final 1/2/4/5/6/7/8 satisfy, 3/9 need complete collection
call sites and raw gate receipts. Two-pass limit reached; no third review.
Its 34-check browser proof and three tested code repairs are on main.

Other holds: AR-168/160 same-candidate native Windows/paired artifact proof;
AR-159 hosted enforcement/check-app/bypass; AR-156 Windows/profile and hosted
topology; AR-135 attended ZCode; AR-140 supported-runner performance;
AR-129/130/147 native Windows; AR-119/125 five-host/matched-value evidence.
AR-176 keeps six stale fixtures; AR-151's nine and AR-157's two are repaired.
Ordinary-session unverified Agency/header behavior remains open.

## Same-task continuity

Own one worktree per record; never stage others' work or commit to main.
Each substantive commit gets an immediate narrow docs(worklog) ledger.
At 50 percent ensure a clean checkpoint and continue the same task.
No empty commits, staffing or restart. Preserve verdicts before corrections.

## Next bounded work package

1. Commit AR-173 focused regression/record checkpoint and immediate ledger.
2. Run broader focused checks/UI/named spine, record raw gates, freeze packet.
3. Five isolated checks, one normal PR/merge/readback, then AR-174.
   No native Windows work and at most two review passes.

## Verification

Two real loopback regression tests; formatting/lint checks. Full current checks
follow this checkpoint. No exhaustive corpus/coverage/matrix dispatch.
AR-165's curated conformance and AR-172's routing results are earlier evidence,
not new runs or live staffing proof.

## Constraints

No credentials, trust bypass or provider-policy changes. The new stale-hook
directive was followed once again: refresh exits 1, activation required,
hook trust unverified and mixed installed projections. No retry absent a new
directive. Do not replace OpenClaw or claim normal-session activation.
