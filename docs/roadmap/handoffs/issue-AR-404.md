---
title: "AR-404 oldest-first backlog completion handoff"
status: active
category: roadmap
created: 2026-09-05
updated: 2026-09-07
tags: [handoff, backlog, acceptance, delivery]
related:
  - docs/roadmap/issue-AR-404-evidence-led-backlog-completion.md
  - docs/roadmap/issue-AR-175-retire-dashboard-control-fallback.md
  - docs/roadmap/acceptance/evidence/AR-175-control-boundary-20260907.md
  - docs/roadmap/AR-404-oldest-first-reconciliation-20260905.md
  - docs/roadmap/issue-AR-176-align-full-gate-contract-fixtures.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-404
branch: codex/ar175-oldest-first-reconciliation
evidence_commit: 7f403ab73fc586a3b130c57e74c9da5d10ad609d
minimum_ledger_commit: 7f403ab73fc586a3b130c57e74c9da5d10ad609d
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/672
---

# AR-404 oldest-first backlog completion handoff

## Checkpoint

Owner resumed September 7 at 20:14 UTC until 21:00 America/New_York,
September 8 at 01:00 UTC. Finish at a clean durable checkpoint by that cutoff.
One record, one normal PR/merge/readback, then next. Native Windows excluded.
AR-173 merged PR #722 at 7ad0d33e; AR-174 merged PR #723 at 57a70139,
September 7 20:41:36Z. Main clean/fast-forwarded before this owned AR-175 tree;
7f403ab7 records the merge. Current count is 120 (40 mapped/80 legacy).

## Completed evidence

AR-175's legacy control fallback is already gone. New direct tests reproduce
eight schema/JSON failures losing request IDs across full and control refresh;
404/network failures and cancellations already behave. Schema validation now
uses the existing API validation callback, preserving request IDs without
fallback. All 20 new cases pass, including aborted/suspended/obsolete work,
exact no-legacy request lists and retained config/roster/control/live state.

Full UI: 224 passes, 96.93/86.78/95.74 coverage. Actual asset/floor tests: four
pass. Assets total 386965 bytes, 107 below unchanged 378 KiB ceiling; repair
removes 74 bytes. Fresh named spine: 1085 passes/three existing skips, 69.72s.
Receipt keeps all eight red failures. Draft docs validation rejected file-URI
stack prefixes; only display schemes are stripped, not failure evidence.

The reusable browser checker now tests 24 schema/JSON faults across both
refresh methods at three viewport widths, recording safe IDs, no legacy GETs,
retained state, recovery and zero POSTs. It has not run yet. Commit clean source
and ledger before building the exact wheel and executing this private fixture.
Only obsolete criterion 6 follows existing ADR-0105; originals preserved.

## Exact blocker

AR-175 is not accepted. Private wheel-backed browser proof, complete current
record evidence and six isolated criteria remain. No native host evidence is
claimed. Do not close AR-170's separate remaining obligations.

AR-174's eight final criteria satisfy at 5a003a05; first verdicts remain at
5d20ec28. ADR-0233 separates dated raw timing from account repair. Historical
PR #380/run 33426445699 measures 366 raw runner-seconds; no current billing or
savings claim. All of that completion is now on main.

Retained holds remain in the oldest-first ledger: AR-170 exhausted review;
AR-168/160 native producer comparison; AR-159 hosted enforcement; AR-156
Windows/profile; AR-135 attended ZCode; AR-140 supported runner; AR-129/130/147
Windows; AR-119/125 five-host matched-value proof. AR-176 retains six fixtures.

## Same-task continuity

Owned worktrees only; never commit main or stage another worker's files.
Each substantive commit gets an immediate narrow docs(worklog) ledger.
At/below 50 percent ensure a clean checkpoint, then continue in this task.
Preserve first verdicts before corrections; two review passes by default.

## Next bounded work package

1. Checkpoint AR-175's tested source/receipt and exact ledger.
2. Build a clean candidate wheel and run the private loaded-browser checker.
3. Finish six isolated criteria, normal PR/merge/readback, then AR-176.
4. Stop cleanly by September 8 01:00 UTC.

## Verification

Current commands and raw red/green/UI/spine/asset outputs are in the receipt.
No exhaustive corpus, coverage shards, compatibility matrix or native Windows
execution. Python product bytes are unchanged; JavaScript and the optional
browser checker change. Prior conformance is not a new run or live staffing.

## Constraints

No credentials, provider policy, billing/settings or trust bypass changes.
Installed Codex refresh previously exited 1 with unverified trust and mixed
package projections; do not retry absent a new directive or replace OpenClaw.
Do not claim ordinary-session activation or specialist staffing.
