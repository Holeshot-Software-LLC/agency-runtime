---
title: "AR-404 oldest-first backlog completion handoff"
status: active
category: roadmap
created: 2026-09-05
updated: 2026-09-07
tags: [handoff, backlog, acceptance, delivery]
related:
  - docs/decisions/0232-represent-route-lab-observations-by-trace-digest.md
  - docs/roadmap/acceptance/issue-AR-173.md
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
evidence_commit: 594bc4d3939d144440ae52f5acdf5f840c79f25e
minimum_ledger_commit: 2856ac53cfd45933f5d4f10518c56670283333da
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/672
---

# AR-404 oldest-first backlog completion handoff

## Checkpoint

Owner resumed September 7 at 20:14 UTC, authorizing oldest-first sequential
delivery until 21:00 America/New_York (September 8 at 01:00 UTC). Finish at a
clean durable checkpoint by that cutoff. Native Windows remains with the owner.
The accepted AR-173 pause checkpoint is 1f16f948. Main remains clean at 47d40fec,
PR #721's AR-172 merge. Publish AR-173 first; 6afcbcb5 records the prior merge.

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
- Full dashboard/explanation/observability: 195 pass, 52.75s.
- UI 204 pass; 96.93/86.78/95.73 meets unchanged floors. Named spine:
  1085 pass/three existing skips, 69.18s. Raw transcripts are recorded.
- No production change. ADR-0231 reconciled 1/4/5; explicit successor ADR-0232
  also corrects criterion 2's raw-trace/digest confusion. Originals remain.
- Draft record failures (missing transcript headings, then Node display padding)
  are preserved. The final contract passes all record gates: 1207 Markdown
  files, 397 mapped/two historical PR exceptions, Ruff and diff clean.
- All five final-candidate verdicts satisfy at 594bc4d3. First review remains
  at 941b9025; no copied verdicts or third review.
- Accepted AR-173's branch has 40 mapped plus 81 legacy, 121 unfinished.
  Main still has 40 mapped plus 82 legacy, 122, until publication resumes.

## Exact blocker

No AR-173 technical acceptance blocker remains. All five criteria satisfy at
594bc4d3; the explicit continue request lifts the owner pause. Publish the
accepted completion and ledger without another acceptance pass. First verdicts
and requirement changes remain preserved.

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

1. Publish accepted AR-173 as one normal PR; no acceptance rerun needed.
2. Stop at a clean checkpoint by September 8 at 01:00 UTC (9 p.m. Eastern).
3. Merge/read back before inspecting AR-174. No native Windows work.

## Verification

Real loopback regression, full focused suites, UI/current floors, named spine
and full strict record checks pass. No exhaustive corpus/coverage/matrix dispatch.
AR-165's curated conformance and AR-172's routing results are earlier evidence,
not new runs or live staffing proof.

## Constraints

No credentials, trust bypass or provider-policy changes. The new stale-hook
directive was followed once again: refresh exits 1, activation required,
hook trust unverified and mixed installed projections. No retry absent a new
directive. Do not replace OpenClaw or claim normal-session activation.
