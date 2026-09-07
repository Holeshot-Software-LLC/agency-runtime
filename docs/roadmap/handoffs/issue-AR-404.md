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
  - docs/roadmap/issue-AR-156-restore-cost-bounded-verification.md
  - docs/roadmap/acceptance/evidence/AR-156-verification-workflow-20260907.md
  - docs/roadmap/issue-AR-157-quiet-public-http-disconnects.md
  - docs/roadmap/issue-AR-176-align-full-gate-contract-fixtures.md
  - docs/roadmap/issue-AR-135-complete-zcode-integration.md
  - docs/roadmap/issue-AR-140-scale-routing-and-retrieval.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-404
branch: codex/ar156-oldest-first-reconciliation
evidence_commit: 9fb95136db78b05c73da3fbfddf12dc14c4f3827
minimum_ledger_commit: dccb4e8502d8f35de74ed5a68915272df520a32a
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/672
---

# AR-404 oldest-first backlog completion handoff

## Checkpoint

Owner resumed: oldest first, one record/PR/merge, then next, without routine
approval stops. Windows stays with the owner. Sequential history and exact
dispositions live in the oldest-first ledger, not duplicated here.

AR-153 accepted at ea577285, PR #705 merged 8b36ea28 (07:06:14Z).
AR-154 accepted at e1c3069c, PR #706 merged 434175f0 (07:17:59Z).
AR-155 accepted at 6ed24943, PR #707 merged 729e7dc4 (07:34:42Z).
All times September 7. Main was clean and fast-forwarded before the AR-156
worktree; prior-merge ledger 38af9f61. AR-155's four initial passes and unavailable
criterion 3 remain at a3e00bd5; one unchanged-candidate retry supplied its fifth
pass. No repeated accepted checks or fabricated verifier result.

Current AR-156 is retained open. Fix missing-Node false success before any local
gate executes; pin identical local/hosted/documented UI argv and keep all floors.
Reconcile stale branch/push guidance without changing events or matrix.
Three comment-only edits restore the existing asset bound: 387,058 < 387,072
bytes, margin 14; every non-comment JavaScript byte is unchanged.
Repair 9fb95136 and ledger dccb4e85 are committed. The exact rebuilt wheel
passes all 21 private/offline browser checks; normal PR publication remains.

## Completed evidence

- New Node/command tests: initial three failed/six passed (0.21s), then all nine
  pass (0.10s); including restored asset guard, ten pass (0.12s).
- Complete fast workflow files with Windows-named cases excluded: 165 pass,
  five deselected, no skips/failures (4.82s). Real local timeout reaps a peer
  and descendant; structural Windows job checks are not native Windows proof.
- Fresh named 29-module spine: 1085 pass, three existing skips (68.41s).
  Python runtime/named tests have not changed since that run.
- Full UI after comment compaction: 188 pass (250.23ms), no skips/failures,
  production coverage 96.93/86.71/95.71 above unchanged 95/86/93.
- Canonical clean dccb4e85 wheel: all ten served assets match the installation;
  21 loaded views at 1280/1024/375 pass, with no automatic axe violations,
  overflow, clipping or unexpected errors. Poll preservation, keyboard scroll
  and injected failure/correlated stale state/recovery pass at every width.
  Report observed 07:56:53Z; wheel/report hashes and three screenshots are in
  the evidence. Incomplete contrast checks remain; no full WCAG/native claim.
- Broad pre-compaction workflow: 145 pass/one asset failure/five deselected.
  Profile/local-loop selection: 17 pass/four fail/29 deselected. All five
  failures reproduce together on untouched main 729e7dc4 (0.68s).
- Four unmarked profile tests expect Windows-only auto-loader states on Linux;
  production correctly returns unsupported-runtime. Their native Windows
  work remains with the owner, with no guard weakening or test skips added.
- Read-only hosted inspection: CI active, latest listed run August 31,
  cancelled at c6e9e46c. No current hosted pass or current billing diagnosis.
- Count unchanged: 40 actual open trackers plus 91 unfinished legacy records,
  131 local unfinished. AR-156's thirteen original criteria stay unchanged.

## Exact blocker

AR-156 still needs separately authorized hosted topology evidence and native
Windows/profile evidence. Historical 74.444-percent local speedup and the
under-threshold timing-profile promotion remain old-candidate results.
Exhaustive coverage/matrix are optional diagnostics under ADR-0105, not a
reason to spend or retry during this bounded package.

Retained independent holds: AR-135 needs attended installed ZCode Agent/
record-zero/full Stop proof; discovery/registration/enablement are not loading.
AR-140 retains isolated supported-runner performance proof, including Windows.
AR-129/130 and Windows-only AR-147 stay with the owner. AR-119/125 retain
five-host and matched-value evidence. AR-176 owns six stale fixtures from
AR-127/130/131; AR-151 already repaired its nine separate dashboard fixtures.
Ordinary-session unverified staffing/header remains an unfinished concern.

## Same-task continuity

Use one owned worktree/branch per item, never commit to main. Substantive commit
then immediate narrow docs(worklog) ledger; record prior merge in the next tree.
Preserve unrelated staged changes in other worktrees. At 50 percent, ensure a
clean evidence/ledger checkpoint, then continue the same task without a restart.

## Next bounded work package

1. Publish the scoped artifact receipt and ledger; keep AR-156 open.
2. Complete docs/tracker checks, merge one PR normally and read back its SHA.
3. Fast-forward clean main; begin the separate AR-157 worktree.

## Verification

Evidence: acceptance/evidence/AR-156-verification-workflow-20260907.md.
Run metadata, policy availability, exact worklog, strict docs/tracker, Ruff and
diff checks per package. New fast gate regressions are in both workflow lists.
Retain the failed Linux profile receipt, not a full-suite pass. No fresh full
corpus, aggregate Python coverage, interpreter matrix or native Windows claim.
The graphify graph is absent; bounded source inspection is used, no graph build
or subagent staffing.

## Constraints

No credential creation, human-trust bypass, unmanaged gateway restart or provider
policy change. Runtime-requested Codex refreshes return exit 1: files registered,
activation required, hook trust unverified and mixed installed projections.
Do not retry or replace OpenClaw as part of backlog cleanup. Staged files and
generated smoke do not establish normal-session activation.
