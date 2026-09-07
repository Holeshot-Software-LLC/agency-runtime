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
  - docs/roadmap/issue-AR-158-disambiguate-multi-surface-observation-tests.md
  - docs/roadmap/acceptance/evidence/AR-158-observation-selection-20260907.md
  - docs/roadmap/issue-AR-159-enforce-production-branch-protection.md
  - docs/roadmap/issue-AR-156-restore-cost-bounded-verification.md
  - docs/roadmap/issue-AR-176-align-full-gate-contract-fixtures.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-404
branch: codex/ar158-oldest-first-reconciliation
evidence_commit: 95085a3008389fadf8c4c99123cf3eacfc8e1925
minimum_ledger_commit: ce37c21a6fed9d931a2205508615852cf92a2342
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/672
---

# AR-404 oldest-first backlog completion handoff

## Checkpoint

Owner resumed: one oldest record, one PR, normal merge, then next; no routine
approval pauses. Windows remains with the owner. The oldest-first ledger owns
the full exact history.

AR-156 retained open; PR #708 merged 6b4650b3 at 08:00:11Z September 7.
AR-157's six criteria satisfy at a35657e1; PR #709 merged ea6864b1 at
08:17:39Z. Clean main was fast-forwarded before this AR-158 tree. Prior merge
is recorded in ledger 38f2a733.

AR-158: existing MCP/HTTP exact selectors remain. Removed old hook proof
belonged to retired child denial (20f006b6); current three-host prompt failure
tests now verify real content-free degraded/boundary_failure observations,
after unrelated Store injection, while preserving North Star R8 publication.
Store busy selection now requires its explicit request ID; slow/busy tests
inject matching unrelated events and check privacy over every envelope.
Nested Store-before-MCP order remains exact-ID scoped. No runtime/script change.
Only criterion 7 is reconciled under ADR-0105; first six stay unchanged.
Candidate 95085a30 and ledger ce37c21a are committed; seven builder rowsets
are frozen against that exact candidate in acceptance/issue-AR-158.md.

## Completed evidence

- Exact MCP/HTTP/three-host plus full Store/runtime observation focus: 13 pass,
  zero skips/failures (1.22s).
- Five interface cases in ten fresh pytest processes: 50 pass total, no skips
  or failures, each run 0.63–0.65s.
- Complete hook-logging, host-hooks, MCP, runtime/Store observation package:
  135 pass, five existing skips, no failures/deselections (36.16s).
- All runtime/scripts equal clean dccb4e85. Tests equal a35657e1 except the three
  changed modules, none in the named spine. Reuse AR-156's 1085-spine/three-skip,
  UI 188/current floors, and ten-asset/21-loaded-view wheel receipts.
- Ruff check/format pass, 766 files. Latest telemetry 27.6 percent at 08:22:27Z;
  finish this small evidence/ledger checkpoint before isolated verification.
- Counts remain 40 actual open trackers plus 90 unfinished legacy records
  (130 local unfinished). Seven AR-158 verdicts remain before completion.

## Exact blocker

No known product blocker for scoped AR-158; isolated acceptance is pending.
Existing skips are recorded, not new suppression.

Independent holds: AR-156 needs owner Windows/profile and separately authorized
hosted topology proof; all thirteen criteria remain. Its four Windows-profile
assumptions fail unchanged Linux main. Latest listed CI is August 31/cancelled,
not current proof or a verified billing diagnosis. AR-135 needs attended ZCode
Agent/record-zero/full Stop proof. AR-140 retains supported-runner performance
including Windows. AR-129/130/147 stay with the owner; AR-119/125 retain five-host
and matched-value proof. AR-176 keeps six separately recorded stale fixtures;
AR-151's nine dashboard and AR-157's two HTTP repairs are not pending.
Ordinary-session unverified Agency/header remains unfinished.

## Same-task continuity

Own one worktree/branch per record. Never commit to main or stage others' work.
Each substantive commit gets its immediately following narrow docs(worklog)
ledger; record the prior merge in the next tree. At 50 percent ensure a clean
checkpoint, then continue the same task. No empty commits, restart or staffing.

## Next bounded work package

1. Run the seven frozen isolated acceptance checks at 95085a30.
2. Preserve any failed verdict before revision; never handwrite a result.
3. If all seven satisfy, mark done, reconcile counts, merge one normal PR,
   read back the actual merge SHA and fast-forward clean main.
4. Start AR-159 separately; branch/account settings require explicit authority.

## Verification

Evidence: acceptance/evidence/AR-158-observation-selection-20260907.md.
Run metadata, policy, exact worklog, strict docs/tracker, Ruff and diff checks.
No new corpus, aggregate coverage, native Windows, exhaustive matrix or host
installation is claimed. Reused results name their exact unchanged bytes.
The graphify graph is absent; use bounded source inspection, no graph build.

## Constraints

No credential creation, trust bypass, unmanaged restart or provider-policy
change. Runtime-requested Codex refreshes return exit 1: activation required,
hook trust unverified, mixed installed projections. Do not retry unattended
or replace OpenClaw. Registration/generated smoke is not normal-session proof.
