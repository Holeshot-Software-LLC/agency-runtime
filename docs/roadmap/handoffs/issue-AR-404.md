---
title: "AR-404 evidence-led backlog completion handoff"
status: active
category: roadmap
created: 2026-09-05
updated: 2026-09-05
tags: [handoff, backlog, acceptance, delivery]
related:
  - docs/roadmap/AR-404-backlog-dispositions-20260905.md
  - docs/roadmap/acceptance/issue-AR-285.md
  - docs/roadmap/issue-AR-405-make-directory-identity-regressions-portable.md
  - docs/roadmap/issue-AR-404-evidence-led-backlog-completion.md
  - docs/roadmap/AR-404-backlog-inventory-20260905.md
  - docs/roadmap/handoffs/issue-AR-400.md
  - docs/roadmap/issue-AR-348-enforce-strict-independence-in-production.md
  - docs/roadmap/issue-AR-349-persist-rejected-hiring-cases.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-404
branch: codex/ar405-portable-directory-identity
evidence_commit: 970293d7c315df955080635f88223e72734bdd72
minimum_ledger_commit: 92b6f13cccbeb43f6a1043ea4f4fd6b09b0596ee
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/672
---

# AR-404 evidence-led backlog completion handoff

## Checkpoint

The owner asked to commit review artifacts, plan and implement the findings,
then clean up and complete the backlog. This item owns the full baseline, not
just the completed review slice. The latest request prioritizes semantically
triaging done, contradictory and unwanted records before more implementation.
Umbrella phase: implementing. The first record package is pushed and merged
through PR #676 and ledger #677; origin/main is 3ed51069. The owner asked to
push and continue. The current AR-405 test-only package repairs the reproduced
Linux failures and reaches its local observable demo; all three isolated
acceptance criteria are satisfied against 593f074f. Protected conformance passed
its baseline and 182/182 mutations; PR #678 carries the completed outcome.
AR-271 is next. No implementation agents were delegated.

## Completed evidence

- Baseline inventory: 155 unfinished records, 56 open and 99 in_progress;
  105 p0 labels. Five acceptance files at inventory time, only two before the
  current package created its builder records. All 155 have an assigned lane;
  this is planning, not semantic verification of every record.
- AR-400/401/402/403 fixes merged in PR #669 at 1de05aea and installed from a
  non-editable pinned build; projection 349f1ae7fc74.
- All five deterministic host contracts pass. Claude isolated native-child
  canary passed at 16:51Z, including code-reviewer delivery and final header.
- Twelve isolated acceptance criteria for those four issues now satisfied.
  The first three absent judgments lacked production-wiring excerpts; their
  original verdicts are preserved in 606065f2 and the augmented excerpts were
  re-verified once. No judgment was written by the builder.
- Latest focused regression: 228 passed, one skipped. Previous named fast
  spine 1004 passed/three skipped, JS 138, routing pass, 182 mutation kills.
- Missing AR-398/399 trackers mapped to #670/#671 and closed against existing
  acceptance; stale-open AR-397 #654 also closed. The four accepted review
  issues close with the delivery PR; verify_tracker confirms resulting parity.
- After the four review closures, 151 baseline items remain plus AR-404.
- First semantic batch retires AR-132/167/169/267, preserves original criteria
  and records successors. ADR-0219 retires helper-specific release/signing
  obligations while keeping the existing two wheel profiles and cross-OS proof.
- AR-285 offline parent/current replay reproduces unknown before the repair and
  proven stopped now, plus eleven current negative/legacy cases. Focused
  installer/registration suite: 181 passed in 4.49 seconds. Builder record cites
  historical stopped-host install receipts separately. Isolated verifier: criteria
  1/3/4 satisfied, 2/5 absent. Missing trusted-runner wiring citation and successful
  changed-precondition dry-run receipt keep the issue open; its two boxes reopen.
- Wider focused run: 443 passed, two skipped, two failed on Linux-only absence
  of Windows file attributes. Filed AR-405 (#675); no code was changed.
- Next AR-405 package reproduces 91 pass/two fail in the build-test file,
  then returns 100 pass/one native-only skip after a test-only correction.
  Portable real directory I/O and same-path replacement remain asserted;
  synthetic volatile-bit, wrong-kind, reparse, inode and device cases run on Linux.
  Wider focused run is now 452 pass/three skips. Named fast spine 1004 pass/three
  skips (63.23s), UI 138 pass. Windows execution remains explicitly unavailable.
  Production identity logic and installed runtime payload are unchanged.
- AR-405 Codex isolated runs 124a4504/c63ec485/346df944 satisfy all three
  criteria. The unmodified conformance command first failed its baseline's
  private-directory boundary under inherited umask 0002; no mutations ran and
  source was unchanged. The protected umask 077 rerun passed its baseline
  (99.433s), killed 182/182 mutations with zero invalid/survived and no source drift.
- First record checkpoint: 147 unfinished baseline records plus AR-404 and AR-405.
- AR-405 completion: 147 unfinished baseline records plus AR-404 (148 total).
- Named fast spine: 1004 passed, three skipped in 64.18 seconds; UI 138 passed;
  docs/acceptance/tracker/distribution-verifier focused tests 207 passed.
  Ruff, format, metadata, policy, worklog and strict docs/tracker checks pass.
  Routing and decision conformance pass; source remains unchanged.
- Claude acceptance verification recorded nothing: read-only transport inspection
  reports an untrusted substitutable executable parent namespace. Codex transport
  supplied the supported excerpt-only verification above. No second judgment
  pass was used to force a successful verdict.
  No host permissions, trust settings or credentials were changed.

## Exact blocker

AR-285 is not done: its two absent evidence criteria are retained. AR-405's
Linux test repair is implemented, locally demonstrated and isolated-accepted;
its final verification passed and PR #678 carries its delivery.
No exhaustive workflow, Windows run, host trust bypass or service interruption
was performed. This turn's requested Codex install refresh found current files;
attended hook trust remains unverified and the running process remains stale.

The entire backlog is not complete. AR-348 was reproduced against current
production hiring with fake valid replies in a disposable Store:
strict_independence=true still returned hired and created a worker on one
provider. AR-349 still returns an in-memory rejection without a case and its
existing test asserts hiring_case is None. Neither was changed by AR-400.

Native rollout: Codex requires attended trust of eight changed hooks in a fresh
terminal TUI; OpenClaw requires permission to stop/restart the gateway; Hermes
and ZCode need supported ordinary-session proof (no bounded native-child
canary backend here; ZCode has no discovered CLI). These are not general
permission to stop unrelated work or waive proof.

## Same-task continuity

Keep source work in an owned branch/worktree, merge by PR, update exact ledgers.
Installed runtime stays pinned to code 1de05aea until another runtime change;
documentation-only delivery commits do not require another payload install.
Current global settings, gateway credentials and historical receipts were not
rewritten. The old PATH launcher was backed up before its interpreter changed.

## Next bounded work package

1. Finish AR-405 isolated acceptance and PR/ledger delivery, then implement the
   genuine AR-271 uninstall classifier gap with last-moment safety regressions.
2. Preserve AR-285's two evidence gaps; add actual trusted-runner wiring citations
   and recover the successful changed-precondition dry-run receipt or obtain
   authority for a fresh bounded proof. Never turn absent verdicts into done.
3. Verify implemented inspection/observability work such as AR-298; reconcile
   AR-337's four-host battery versus all-supported-harness wording and AR-351's
   obsolete domain-axis clause before implementing old proposals.
4. Deliver AR-348/349 hiring-safety gaps as separate packages.
5. Continue AR-253 quality/latency proof and explicitly reconcile AR-393's
   impossible retroactive-receipt wording. No historical data rewrite.

## Verification

Run focused production-path regressions and the repository named fast spine,
then one bounded observable demo per package. verify_docs --require-tracker and
verify_tracker govern record parity; verify_acceptance supplies isolated
criterion verdicts. No exhaustive corpus, coverage matrix or workflow dispatch
was run in the current package.

## Constraints

No direct main commits, native trust bypass, unattended service interruption,
credential creation or hidden provider changes. Do not implement superseded
proposals just to check boxes. Scope every claim and keep platform/operator
exits visible. Never mark AR-404 done while any baseline item is unaccounted.
