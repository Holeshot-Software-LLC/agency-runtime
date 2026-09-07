---
title: "AR-404 oldest-first backlog completion handoff"
status: active
category: roadmap
created: 2026-09-05
updated: 2026-09-07
tags: [handoff, backlog, acceptance, delivery]
related:
  - docs/roadmap/issue-AR-404-evidence-led-backlog-completion.md
  - docs/roadmap/AR-404-oldest-first-reconciliation-20260905.md
  - docs/roadmap/AR-404-count-reconciliation-20260905.md
  - docs/roadmap/issue-AR-157-quiet-public-http-disconnects.md
  - docs/roadmap/acceptance/evidence/AR-157-http-disconnects-20260907.md
  - docs/roadmap/issue-AR-158-disambiguate-multi-surface-observation-tests.md
  - docs/roadmap/issue-AR-156-restore-cost-bounded-verification.md
  - docs/roadmap/issue-AR-176-align-full-gate-contract-fixtures.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-404
branch: codex/ar157-oldest-first-reconciliation
evidence_commit: 2329a3a3eb0349128183b2057b7bd97396906004
minimum_ledger_commit: 2329a3a3eb0349128183b2057b7bd97396906004
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/672
---

# AR-404 oldest-first backlog completion handoff

## Checkpoint

Owner resumed: oldest first, one record/PR/merge, then next, no routine approval
stops. Windows stays with the owner. The oldest-first ledger owns exact history.

AR-155 accepted at 6ed24943, PR #707 merged 729e7dc4 (September 7 07:34:42Z).
AR-156 retained open with local verification repairs 9fb95136 and packaged
receipt ba1b6fa8; PR #708 merged 6b4650b3 at 08:00:11Z. Main was clean and
fast-forwarded before this separate AR-157 tree; merge ledger 2329a3a3.

Current AR-157: the 12640d0 HTTP disconnect implementation already exists.
Two primary-disconnect tests now enter the actual observation boundary and
assert exact degraded/client_disconnected evidence with private query/body/error
sentinels excluded from logs. Two stale HTTP fixtures are repaired at their
actual seams; runtime/scripts bytes remain unchanged. First five acceptance
criteria are unchanged, sixth explicitly reconciled to ADR-0105. Not done yet.

## Completed evidence

- Initial public/dashboard disconnect pair: 26 pass (0.52s).
- Initial full HTTP/disconnect/runtime-observation package: 102 pass, two
  failures, three existing inference skips (22.62s). Both failing fixtures
  reproduce on untouched main 6b4650b3 (two failed, 3.01s).
- Fixed roster count compares to actual enabled Store catalog, not a new magic
  number. Resident-worker admission test explicitly seeds one real suggestion,
  then requires exact row preservation and parent-only rejection at HTTP 400.
- Revised pair plus two repaired HTTP cases: 28 pass (1.83s).
- Final complete four-module package: 104 pass, three existing skips, no
  failures/deselections (22.25s). Shared transport coverage: 11 statements,
  four branches, zero misses/partial branches, 100 percent. Not aggregate coverage.
- All runtime/scripts and all tests except those two equal clean dccb4e85.
  Neither changed test belongs to the named spine: reuse AR-156's 1085 passes/
  three skips (68.41s), unchanged UI 188 and coverage 96.93/86.71/95.71.
- Reuse exact clean dccb4e85 wheel's ten matching assets, 21 loaded browser
  checks and all three polling/fault-recovery interactions. No new install.
- Ruff check/format pass, 766 files. Latest telemetry 52.9 percent at 08:05:53Z.
- Current count: 40 actual open trackers plus 91 unfinished legacy records
  (131 local unfinished). Six isolated AR-157 verdicts remain before closure.

## Exact blocker

No product blocker is known for scoped AR-157; acceptance review is pending.
Existing inference-flow skips are explicit, not new test suppression.

Independent retained holds: AR-156 needs native Windows/profile and separately
authorized hosted topology evidence; its thirteen criteria remain unchanged.
Four profile assumptions fail on Linux unchanged main. Latest listed hosted
CI is August 31/cancelled, not current evidence or a verified billing diagnosis.
AR-135 needs attended installed ZCode Agent/record-zero/full Stop proof.
AR-140 retains isolated supported-runner performance evidence, including Windows.
AR-129/130 and Windows-only AR-147 remain owner work; AR-119/125 retain
five-host/matched-value proof. AR-176 keeps six separately recorded stale cases;
AR-151's nine dashboard and AR-157's two HTTP fixture repairs are not pending.
Ordinary-session unverified Agency/header behavior remains unfinished.

## Same-task continuity

Use an owned worktree/branch per record, never commit to main. Follow every
substantive commit immediately with its narrow docs(worklog) ledger; record
the previous merge in the next tree. Preserve unrelated staged work elsewhere.
At 50 percent, finish a clean evidence/ledger checkpoint and continue the same
task. No restart, subagent staffing, empty checkpoint or optional exhaustive run.

## Next bounded work package

1. Commit AR-157 tests/evidence and ledger; freeze six builder evidence rowsets
   against that exact candidate and run isolated single-criterion verification.
2. Preserve any failed verdict before changes; never handwrite acceptance.
3. If all six satisfy, mark done, update counts, publish one normal PR, read
   back its actual merge SHA and fast-forward clean main.
4. Begin the separate AR-158 worktree after merge.

## Verification

Evidence: acceptance/evidence/AR-157-http-disconnects-20260907.md.
Run metadata, policy availability, exact worklog, strict docs/tracker, Ruff and
diff checks. Full corpus/aggregate coverage/matrix remain optional under
ADR-0105. Native Windows code representations in tests are not native execution.
The graphify graph is absent; bounded source inspection is used without a build.

## Constraints

No credential creation, trust bypass, unmanaged gateway restart or provider
policy change. Runtime-requested Codex refreshes return exit 1: files registered,
activation required, hook trust unverified and mixed installed projections.
Do not autonomously retry or replace OpenClaw. Generated smoke/registration
cannot establish normal-session activation.
