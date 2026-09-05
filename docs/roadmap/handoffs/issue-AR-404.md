---
title: "AR-404 evidence-led backlog completion handoff"
status: active
category: roadmap
created: 2026-09-05
updated: 2026-09-05
tags: [handoff, backlog, acceptance, delivery]
related:
  - docs/roadmap/acceptance/evidence/AR-348-installed-delivery-20260905.md
  - docs/roadmap/acceptance/issue-AR-348.md
  - docs/roadmap/acceptance/issue-AR-406.md
  - docs/roadmap/acceptance/issue-AR-152.md
  - docs/roadmap/acceptance/evidence/AR-406-production-coverage-20260905.md
  - docs/decisions/0220-measure-dashboard-coverage-over-production-modules.md
  - docs/roadmap/acceptance/issue-AR-148.md
  - docs/roadmap/acceptance/issue-AR-323.md
  - docs/roadmap/acceptance/evidence/AR-323-current-schema-verification-20260905.md
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
branch: codex/ar348-installed-delivery
evidence_commit: 0309f251c6cf1c6c22b3a4458302c8b2cad78734
minimum_ledger_commit: b2b80a2ceb1fa300669d6e8ec3a7ac4b8193d394
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/672
---

# AR-404 evidence-led backlog completion handoff

## Checkpoint

Owner says continue one by one, leave Windows work to their Windows machine,
close completed records, and judge old agent-authored tickets for present
product relevance instead of treating their designs as instructions.
Main 0309f251 includes PR #687's accepted AR-348 repair after PRs #683..686.
Tracker #406 (AR-348) is closed; #682 was closed in the preceding package.
Exact merged runtime is installed and scoped smoke passes. AR-348 is done;
AR-349 is the next package. No implementation agents were delegated. Umbrella
remains implementing; Windows work stays with the owner.

## Completed evidence

- AR-348 fresh red reproduction at main 6307e17d: 20 failures, 23 passes
  (14.14s). Strict mode silently allows all tested overlaps; controls pass.
  Both reviewer routes, nine resolution sources and safety-repair creators are
  covered through the public hiring entry point. No external inference ran.
  Runtime fix under ADR-0221: 413 focused passes/one skip, 1075 spine passes/
  three skips, UI/routing/Ruff pass. Two added curated mutations have 17 passing
  catalog tests. Both original criteria satisfied against c9b678a5. Protected
  conformance: baseline passes (98.879s), 184/184 killed, zero survived/invalid,
  source unchanged. Earlier umask-0002 fixture failures remain in evidence;
  the successful run uses the documented process-local 0077 boundary.
- The owner's 43 open tracker count is correct at e4255836. The reported 147
  was 43 mapped open trackers plus 104 unfinished local pre-tracker records.
  They are a reconciliation queue, not 104 proved extra defects. Full local
  counts were 240 done, 93 in_progress, 54 open, 11 wont_do (398 records).
  New AR-406/#682 adds one tracked issue; AR-139 is now retired as superseded.
  AR-148/149/152/323/406 accepted. Before AR-348: 43 mapped plus 99 legacy.
  Remote #682 closed 2026-09-05 at 21:35:56 UTC; fresh enumeration confirms 43
  open trackers before AR-348. Tracker #406 closed at 22:20:23Z on 2026-09-05;
  read-back confirms CLOSED and fresh enumeration returns 42 actual open
  issues. Local unfinished is 141: 42 mapped plus 99 legacy, not 141 defects.
- Original-baseline reductions: AR-400..403 accepted; AR-132/167/169/267 retired
  through cited successors; AR-271 accepted. AR-405 was outside the baseline
  and is also accepted. Prior work merged via PRs #669/#673/#676..681. Never
  rewrite the frozen original 155-item inventory.
- Installed immutable build 0.1.0+g0309f251c6cf matches every tracked runtime
  byte. New projection 4329d76058d1; old environment/launcher retained. All 45
  new hiring regressions pass against installed package bytes (11.94s). Eight
  deterministic smoke checks pass, including five generated host contracts.
  Native refresh is partial: Codex files refreshed, attended trust unverified;
  Claude/Hermes/ZCode enabled but runtime unverified; OpenClaw untouched on old
  projection. Dashboard restarted/reachable; installer reports consented repair
  of fourteen Claude entries. No manual permissions or credentials changed.
- AR-149's 6a3bdaa0 fix is still present. Four real HTTP identity/error tests
  pass (1.21s); complete dashboard/disconnect files 180 pass (27.28s). Current
  acceptance exposes four old prose criteria as checkboxes and reconciles
  only the obsolete complete-corpus condition with ADR-0105. Candidate b9d68e5d:
  all four criteria satisfied. The first absent 2/3 verdicts remain in f2e41b89;
  targeted rechecks passed after missing ContextVar/Store excerpts were added.
  Eight boundary/Store tests pass in 0.31s. No product criterion changed.
- AR-152's stable container listener, semantic buttons and 50-render soak pass.
  AR-406's original 91.12 function score included fixture functions. ADR-0220
  explicitly measures all seven production JS modules, retaining 95/86/93 floors.
  Actual configured local command: 138 pass, 96.92/86.62/95.71 coverage. Both
  local/CI exact-command regressions first failed; 163 workflow-contract tests
  now pass. Fresh spine 1030 pass/three skips (64.98s). Product and UI behavioral
  tests unchanged. AR-406 has three satisfied criteria at d109b094; AR-152 has
  four at 12a62393. Initial absent baseline-comparison verdict retained before
  exact equal Git objects were supplied. No criterion or implementation changed.
- AR-139 is retired, not certified against its obsolete 263,168-byte ceiling.
  AR-295 plus 3023f0557 explicitly audited required UI. Current ten assets total
  386,366 bytes and pass the strict 378-KiB resource test (1 pass, 0.17s).
  AR-148's signature guard is present. Wider checks exposed AR-323's known
  schema-46 literals in three ledger cases plus seven migration/credential cases.
  The test-only fix preserves legacy inputs and all behavioral checks: 401
  focused pass, fresh 1030 spine pass/three skips (63.73s). Candidate 11371cb6:
  all eight AR-148/323 isolated criteria satisfied, both done. No new tracker.
  AR-129/130 claim implementation but include Windows proof; leave that with
  the owner. AR-298 has source/tests and old installed visual evidence, but
  no isolated acceptance yet.

## Exact blocker

AR-348 has no remaining bounded-contract blocker: accepted, merged and installed,
with current conformance and scoped smoke. Native live-host limits below remain
separate from that contract. No verification failure is silently relabeled;
failed receipts remain in their bounded evidence records.
Do not claim "most done" before relevance and evidence are examined. Do not
reimplement a historical defect merely because status=open.

AR-348 is fixed; AR-349 remains a reproduced hiring gap. AR-350 needs an owner-authority decision;
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

1. Implement AR-349's rejected-hire persistence as a separate bounded package.
   Reproduce all repair-exhaustion exits, retain safe no-worker behavior, then
   prove durable rejected-case evidence. Do not broaden into staffing redesign.
2. AR-298 remains implemented pending isolated verification. Keep Windows work
   excluded and current provider configuration and attended trust unchanged.
3. Continue historical relevance review: retire superseded proposals with
   reciprocal links; close implemented work only with accepted evidence.

## Verification

Current AR-348 source: 413 focused passes/one skip, 1075 named-spine passes/
three skips, 138 UI cases, routing gates and 184 protected mutation kills.
Both original isolated criteria are satisfied. Exact installed package: 45 new
hiring cases and eight smoke checks pass; all tracked runtime bytes match. The
earlier installed 182-case receipt is not transferred. No new exhaustive Python,
cross-interpreter or Windows run. No test dependency was added to the installed
runtime. ADR-0105 makes exhaustive integration optional. Strict docs/tracker
and exact worklog checks govern parity.

## Constraints

Windows work stays open or explicitly deferred, never closed by Linux tests.
Codex attended hook trust, OpenClaw stop/restart consent and fresh Hermes/ZCode
session proof remain operator boundaries. The existing configured credential is
absent from this shell; no current-build live Claude canary was attempted.
Stale-hook warning: `agency install --agent codex` refreshed files, returned 1
with activation-required/unverified hook trust; no unattended retry or bypass.
No credential creation, trust bypass, unmanaged gateway interruption,
provider-policy change or exhaustive dispatch is authorized by this cleanup.
