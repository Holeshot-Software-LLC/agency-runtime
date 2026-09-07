---
title: "AR-404 oldest-first backlog completion handoff"
status: active
category: roadmap
created: 2026-09-05
updated: 2026-09-07
tags: [handoff, backlog, acceptance, delivery]
related:
  - docs/roadmap/issue-AR-172-make-roster-pages-snapshot-consistent.md
  - docs/roadmap/acceptance/issue-AR-172.md
  - docs/roadmap/acceptance/evidence/AR-172-roster-snapshots-20260907.md
  - docs/roadmap/issue-AR-170-fail-dashboard-response-correlation-closed.md
  - docs/roadmap/issue-AR-404-evidence-led-backlog-completion.md
  - docs/roadmap/AR-404-oldest-first-reconciliation-20260905.md
  - docs/roadmap/issue-AR-176-align-full-gate-contract-fixtures.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-404
branch: codex/ar172-oldest-first-reconciliation
evidence_commit: dec1bc512462285cf4d43742c3e666e6d776186e
minimum_ledger_commit: b59f743a295cfd332eb3430050268990faddf527
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/672
---

# AR-404 oldest-first backlog completion handoff

## Checkpoint

Owner continues one oldest record, one PR, normal merge, then next. Native
Windows remains with the owner. PR #720 merged accepted AR-171 at a846c88f,
12:32:58Z September 7. Main was clean and fast-forwarded before the separate
AR-172 tree; 8f9d9e4c records that merge and is the prior clean checkpoint.

## Completed evidence

AR-172's Store/HTTP/JS implementation is present. One read transaction binds
generation/count/limited rows; configuration and Store revisions bind dashboard
paging. A mismatched control pair recaptures and persistent churn fails closed.
The original three-attempt limit is unchanged, not a new behavior requirement.

- New 81-line table adds ten passing last-good-state tests: both refresh modes
  across initial/primary/exact/operational-initial/operational-page config drift.
- Complete Store/HTTP/activation: 278 pass, 59.46s.
- UI 204 pass, zero skips/failures; 96.93/86.78/95.73 meets unchanged floors.
- Fresh named spine: 1085 pass/three existing skips, 69.71s.
- No production/script/workflow change. Only criterion 7 is reconciled under
  ADR-0105; original wording and first six criteria remain.
- Fresh routing passes 39 candidate-recall-only gates; not staffing evidence.
- Raw transcripts and record gates pass: 1201 Markdown documents, 397 mapped
  trackers/two historical PR exceptions, Ruff and diff clean. Freeze comes next.
- AR-171 done leaves 40 actual trackers plus 83 legacy, 123 unfinished.
  AR-172 remains in_progress until its isolated verdicts satisfy.

## Exact blocker

No reproduced AR-172 production defect. Its first isolated acceptance review is
pending the complete committed evidence packet. Do not flip status early.

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

1. Evidence candidate dec1bc51 and its immediate ledger are committed.
2. Freeze that candidate and run its seven isolated checks, at most two passes.
3. Publish one normal PR/merge/readback, then AR-173. No native Windows work.

## Verification

Fresh Store/HTTP, UI/current coverage, named spine, routing and strict record
checks pass before freeze. No exhaustive corpus/coverage/matrix dispatch.
AR-165's 184/184 curated decision receipt is earlier unchanged Python evidence:
Git comparison of package Python and scripts against 9effff3f exits zero.
This is not a new conformance run or a JS mutation evaluation.

## Constraints

No credentials, trust bypass or provider-policy changes. The new stale-hook
directive was followed once again: refresh exits 1, activation required,
hook trust unverified and mixed installed projections. No retry absent a new
directive. Do not replace OpenClaw or claim normal-session activation.
