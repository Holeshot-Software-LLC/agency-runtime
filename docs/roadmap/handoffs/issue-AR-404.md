---
title: "AR-404 evidence-led backlog completion handoff"
status: active
category: roadmap
created: 2026-09-05
updated: 2026-09-05
tags: [handoff, backlog, acceptance, delivery]
related:
  - docs/roadmap/issue-AR-404-evidence-led-backlog-completion.md
  - docs/roadmap/AR-404-count-reconciliation-20260905.md
  - docs/roadmap/AR-404-backlog-dispositions-20260905.md
  - docs/roadmap/acceptance/issue-AR-149.md
  - docs/roadmap/issue-AR-406-restore-dashboard-function-coverage.md
  - docs/roadmap/acceptance/evidence/AR-271-installed-delivery-20260905.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-404
branch: codex/ar404-close-proven-history
evidence_commit: e425583603a99debc5b6cdbe3c2c84f4f3e7954d
minimum_ledger_commit: e425583603a99debc5b6cdbe3c2c84f4f3e7954d
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/672
---

# AR-404 evidence-led backlog completion handoff

## Checkpoint

Owner says continue one by one, leave Windows work to their Windows machine,
close completed records, and judge old agent-authored tickets for present
product relevance instead of treating their designs as instructions.
Main e4255836 includes all previous delivery and merge-ledger records.
Current package: reconcile counts and close already-shipped historical work.
No implementation agents were delegated. Umbrella remains implementing.

## Completed evidence

- The owner's 43 open tracker count is correct at e4255836. The reported 147
  was 43 mapped open trackers plus 104 unfinished local pre-tracker records.
  They are a reconciliation queue, not 104 proved extra defects. Full local
  counts were 240 done, 93 in_progress, 54 open, 11 wont_do (398 records).
  New AR-406/#682 adds one tracked issue; AR-139 is now retired as superseded.
  Current split: 44 tracked open plus 103 legacy unfinished.
- Original-baseline reductions: AR-400..403 accepted; AR-132/167/169/267 retired
  through cited successors; AR-271 accepted. AR-405 was outside the baseline
  and is also accepted. Prior work merged via PRs #669/#673/#676..681. Never
  rewrite the frozen original 155-item inventory.
- Installed immutable build 0.1.0+g5434836eec4e, projection 1d617ca589a2,
  matches current runtime/test/tool source. Eight deterministic smoke checks,
  five generated host contracts passed; native refresh is partial. Old runtime
  and launcher are retained. Installed evidence records actual side effects.
- AR-149's 6a3bdaa0 fix is still present. Four real HTTP identity/error tests
  pass (1.21s); complete dashboard/disconnect files 180 pass (27.28s). Current
  acceptance exposes four old prose criteria as checkboxes and reconciles
  only the obsolete complete-corpus condition with ADR-0105. Candidate b9d68e5d:
  criteria 1/4 satisfied; 2/3 absent because nested-boundary/Store propagation
  excerpts were omitted. Add those source citations, then recheck only 2/3.
- AR-152's stable container listener, semantic buttons and 50-render soak are
  present and pass. Full UI suite 138 pass, but configured coverage exits 1 on
  Node v22.23.2: 97.80 lines, 88.43 branches, 91.12 functions versus 95/86/93
  floors. AR-406 owns this shared gap; no floor, exclusion or production code
  changed. Do not relabel it green.
- AR-139 is retired, not certified against its obsolete 263,168-byte ceiling.
  AR-295 plus 3023f0557 explicitly audited required UI. Current ten assets total
  386,366 bytes and pass the strict 378-KiB resource test (1 pass, 0.17s).
  AR-148's existing signature guard and release/schema files pass 157 tests.
  AR-129/130 claim implementation but include Windows proof; leave that with
  the owner. AR-298 has source/tests and old installed visual evidence, but
  no isolated acceptance yet.

## Exact blocker

AR-149 needs missing evidence for criteria 2/3, then local closure in PR #683. There is no
reproduced current request-ID defect. AR-152 remains open pending honest
reconciliation of its aggregate coverage clause and current evidence. AR-406
is a current verification gap, not a listener implementation gap.
Do not claim "most done" before relevance and evidence are examined. Do not
reimplement a historical defect merely because status=open.

AR-348/349 are reproduced hiring gaps. AR-350 needs an owner-authority decision;
AR-351's domain proposal conflicts with AR-402/ADR-0217. AR-285 has three
satisfied/two absent historical proof criteria, separate from AR-271.

## Same-task continuity

Owned worktree uses the named branch. Never commit main directly; substantive
commit then immediate narrow docs(worklog) ledger. Freeze acceptance after
evidence exists in an ancestor, run supported Codex excerpt-only single-criterion
verification, and close only satisfied records. Keep legacy tracker exemptions;
do not create duplicate external issues for pre-tracker history.
No current header snapshot exists; no specialist staffing succeeded.

## Next bounded work package

1. Finish AR-149's two missing isolated verdicts and closure, preserving the exact
   validation-scope reconciliation and current UI coverage failure.
2. Continue historical records one by one: retire superseded proposals with
   reasons and reciprocal links; close implemented work with exact evidence.
3. Address AR-406 separately without lowering floors; verify AR-298, then the
   genuine AR-348/349 hiring defects. Keep Windows work excluded.

## Verification

Current bounded tests above plus prior source-identical installed verification:
1030 fast-spine tests, 138 UI cases, routing and 182 conformance mutation kills.
No new exhaustive Python, cross-interpreter or Windows run. ADR-0105 makes
exhaustive integration optional; it does not turn a failed UI coverage command
into a pass. Strict docs/tracker and exact worklog checks govern parity.

## Constraints

Windows work stays open or explicitly deferred, never closed by Linux tests.
Codex attended hook trust, OpenClaw stop/restart consent and fresh Hermes/ZCode
session proof remain operator boundaries. The existing configured credential is
absent from this shell; no current-build live Claude canary was attempted.
Stale-hook warning: `agency install --agent codex` refreshed files, returned 1
with activation-required/unverified hook trust; no unattended retry or bypass.
No credential creation, trust bypass, service interruption, provider-policy
change or exhaustive dispatch is authorized by this cleanup.
