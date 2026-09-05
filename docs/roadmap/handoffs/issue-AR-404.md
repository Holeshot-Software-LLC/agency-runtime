---
title: "AR-404 evidence-led backlog completion handoff"
status: active
category: roadmap
created: 2026-09-05
updated: 2026-09-05
tags: [handoff, backlog, acceptance, delivery]
related:
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
branch: codex/ar404-published-closures
evidence_commit: 853de3106ebc74f3ba6c977722d98f06a969c9c2
minimum_ledger_commit: d17ffcea214a006ca6a986a638bd70bfc0e26d66
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/672
---

# AR-404 evidence-led backlog completion handoff

## Checkpoint

Owner says continue one by one, leave Windows work to their Windows machine,
close completed records, and judge old agent-authored tickets for present
product relevance instead of treating their designs as instructions.
Main 853de310 includes PRs #683/#684: five accepted completions, one retirement.
Tracker #682 is closed; current package records publication and the next outcome.
No implementation agents were delegated. Umbrella remains implementing.

## Completed evidence

- The owner's 43 open tracker count is correct at e4255836. The reported 147
  was 43 mapped open trackers plus 104 unfinished local pre-tracker records.
  They are a reconciliation queue, not 104 proved extra defects. Full local
  counts were 240 done, 93 in_progress, 54 open, 11 wont_do (398 records).
  New AR-406/#682 adds one tracked issue; AR-139 is now retired as superseded.
  AR-148/149/152/323/406 accepted. Local unfinished: 43 mapped plus 99 legacy.
  Remote #682 closed 2026-09-05 at 21:35:56 UTC; fresh enumeration confirms 43
  open trackers. The first immediate REST count briefly lagged at 44.
- Original-baseline reductions: AR-400..403 accepted; AR-132/167/169/267 retired
  through cited successors; AR-271 accepted. AR-405 was outside the baseline
  and is also accepted. Prior work merged via PRs #669/#673/#676..681. Never
  rewrite the frozen original 155-item inventory.
- Installed immutable build 0.1.0+g5434836eec4e, projection 1d617ca589a2,
  matches current production source. Test/gate changes are verified separately.
  Eight prior deterministic smoke checks,
  five generated host contracts passed; native refresh is partial. Old runtime
  and launcher are retained. Installed evidence records actual side effects.
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

PRs #683/#684 are merged and #682 is closed. AR-406/152 have seven satisfied
criteria. The original mixed-scope failure is preserved;
the product scope is explicitly corrected, not relabeled as an original pass.
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

1. AR-348: enforce strict independence over actual resolved creator/reviewer
   chains, covering legacy, harness, fallback and repair paths; preserve
   strict=false warnings. The ticket's declared-profile-only suggestion skips
   legacy routes and is not the specification. Reproduce before changing code.
2. AR-349 follows as a separate rejected-hire persistence package. AR-298 remains
   implemented pending isolated verification. Keep Windows work excluded.
3. Continue historical relevance review: retire superseded proposals with
   reciprocal links; close implemented work only with accepted evidence.

## Verification

Current bounded tests above plus prior source-identical installed verification:
1030 fast-spine tests, 138 UI cases, routing and 182 conformance mutation kills.
No new exhaustive Python, cross-interpreter or Windows run. ADR-0105 makes
exhaustive integration optional; it does not turn a failed UI coverage command
into a pass. Strict docs/tracker and exact worklog checks govern parity.
Fresh routing gates and all 138 UI cases pass. The first conformance invocation
used the installed production interpreter, which has no pytest; baseline failed
before any mutation ran. The development-venv invocation passes its baseline
(98.841s), kills all 182 mutations, and leaves source unchanged. No test
dependency was added to the user's installed runtime.

PR #684 changes only the two coverage commands, their regression, and records.
The publication branch changes records only. Protected conformance inputs remain identical to the preceding
182-kill run; no repeat mutation battery is needed for an unrelated scope flag.

## Constraints

Windows work stays open or explicitly deferred, never closed by Linux tests.
Codex attended hook trust, OpenClaw stop/restart consent and fresh Hermes/ZCode
session proof remain operator boundaries. The existing configured credential is
absent from this shell; no current-build live Claude canary was attempted.
Stale-hook warning: `agency install --agent codex` refreshed files, returned 1
with activation-required/unverified hook trust; no unattended retry or bypass.
No credential creation, trust bypass, service interruption, provider-policy
change or exhaustive dispatch is authorized by this cleanup.
