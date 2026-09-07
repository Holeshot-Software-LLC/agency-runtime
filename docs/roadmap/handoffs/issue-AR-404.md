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
  - docs/roadmap/AR-404-backlog-dispositions-20260905.md
  - docs/roadmap/issue-AR-115-live-routing-trust.md
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-120-normalized-workforce-recruitment-index.md
  - docs/roadmap/issue-AR-125-workforce-and-one-shot-evaluation.md
  - docs/roadmap/issue-AR-127-zcode-stop-rejection-shape.md
  - docs/roadmap/issue-AR-129-isolate-subprocess-environments.md
  - docs/roadmap/issue-AR-130-revalidate-store-trust.md
  - docs/roadmap/issue-AR-131-complete-mcp-cli-host-contracts.md
  - docs/roadmap/issue-AR-176-align-full-gate-contract-fixtures.md
  - docs/decisions/0223-retire-superseded-zcode-stop-checklist.md
  - docs/decisions/0222-retire-superseded-live-routing-contract.md
  - docs/roadmap/acceptance/evidence/AR-348-installed-delivery-20260905.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-404
branch: codex/ar131-oldest-first-reconciliation
evidence_commit: 973acdb991c10e54656990ef0a39db4262adb8be
minimum_ledger_commit: d8656b059b8c89fc40fb37ea532f226bf813c718
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/672
---

# AR-404 oldest-first backlog completion handoff

## Checkpoint

Owner explicitly resumed September 6 at AR-131. Restore oldest-first delivery:
one record, one PR, merge, then next; no routine approval stops. Windows stays
with the owner. Previous pause was delivered by PR #696/f38720c7 and the narrow
PR #697 ledger/c1c5d9d9. No background work ran during the pause.

Current package: AR-131's existing MCP/CLI repair, strengthened current-contract
regressions, and public identifier-admission fix. All six original criteria
now satisfy at 973acdb9; locally done in PR #698, awaiting merge before AR-135.
First candidate fb2e4e23 has verdicts: 2/3/6 satisfied, 1/5 absent citations,
4 contradicted by lossy identifier admission. Those verdicts are preserved at
6a139e23/b7a445a6. Repaired candidate 973acdb9 is frozen with ledger d8656b05:
13 new public-entry regressions pass; the six September 7 isolated verdicts
are recorded. Native normalization remains unchanged.

## Completed evidence

- Prior sequential dispositions and exact publication receipts are in
  AR-404-oldest-first-reconciliation-20260905.md: AR-115/127 retired;
  AR-119/120/125/129/130 retained with real evidence/dependency gaps.
- Current count: 40 actual open trackers plus 98 unfinished legacy records, 138
  local unfinished after AR-131 acceptance. No new tracker or unrelated closure.
  Prior 99/139 inventories remain historical.
- AR-131 base c1c5d9d9: original MCP/CLI tests pass 116/five existing skips.
  Ten new cases cover registry/handler parity, generated status skills for all
  hosts, retired delegation-tool rejection, and exact canonical Store IDs.
  The host-enum check now catches every mismatched host property directly.
  Focused package: 126 passed/five unchanged skips, 6.06s.
- Installed Codex control skill is byte-identical to the current generator.
  This is file evidence, not current session correlation, trust or activation.
- Fresh post-addition named spine: 1085 passed/three skips, 69.18s (baseline
  1075/three, 67.21s). UI: 138 passed; Ruff check/format: 764 files.
  Routing and decision-conformance pass, with conformance source unchanged.
- The old public prepare/delegate/decline tools were removed at eab8c085.
  They must stay absent. Canonical max-sized Store IDs round-trip; arbitrary
  noncanonical internal inputs still have normalization, not an unchanged-byte
  promise. The public facade now rejects lossy inputs before Store recording.
- Repaired alias regression was red before repair; all 13 new cases now pass
  (20.35s), including exact ASCII/Unicode max-sized IDs and no-write rejection.
  Post-repair spine: 1085/three skips (68.60s); UI: 138; routing/Ruff pass.
  Decision-conformance: passing baseline, 184/184 killed, zero survived/invalid,
  source unchanged. No release/installed/live certification.
  Broader nine-module run: 380 pass/one unchanged failure/eight existing skips
  (59.71s). Fallback-roster failure also reproduces on untouched main c1c5d9d9;
  AR-176 owns the sixth stale case. Do not call that run green.
- Earlier AR-348/271 installs and live/deterministic receipts retain their
  original scope. No fresh five-host live pass is claimed by this package.

## Exact blocker

No remaining AR-131 contract-acceptance blocker: all six repaired-candidate
verdicts are satisfied. PR #698 publication/merge remains. Claude verification is unavailable
under executable trust checks; the already usable Codex provider wrote the
six verdicts. No trust or credentials were changed. Native Windows and
earlier installed/live evidence holds remain with their existing owners.
AR-176 owns six stale fixture cases found in AR-127/130/131; none are erased.
The session's unverified staffing/header remains a separate unfinished concern.

## Same-task continuity

Use one owned worktree/branch per item; never commit directly to main.
Substantive commit then immediate narrow docs(worklog) ledger. Record prior
merge in the next worktree. Preserve unrelated staged edits in other trees.
At 50-percent context, commit the smallest safe recovery/ledger pair and
continue the same task. Retained umbrellas cannot be closed by closing one child.

## Next bounded work package

1. Commit the six independent verdicts and local done disposition with an exact
   ledger pair; preserve accepted candidate 973acdb9 and first verdict history.
2. Finish PR #698, verify its final head/check state and merge normally.
3. After the AR-131 disposition merges, review AR-135. AR-132 is retired and
   AR-133/134 are already done. Continue by creation date and AR-number tie break.
   Windows-specific execution stays excluded.

## Verification

Run metadata, policy availability, exact worklog, strict docs/tracker and diff
checks per package; focused checks for touched behavior and the named spine.
No exhaustive corpus/coverage matrix, cross-interpreter matrix or hosted dispatch.
Current detailed receipts: acceptance/evidence/AR-131-current-contracts-20260906.md.
The graphify graph is absent, so orientation used bounded source inspection;
no graph build, specialist selection or native subagent was initiated.

## Constraints

No credential creation, human-trust bypass, unmanaged gateway restart or provider
policy changes. One runtime-requested Codex install returned exit 1: registered,
activation required, trust unverified, mixed installed projections. No retry or
OpenClaw replacement. Codex hook trust and session correlation are not proven by a
matching installed skill file. Claude/Hermes/ZCode enablement is not live proof;
the prior OpenClaw gateway held an older package. Do not create duplicate
trackers for exempt pre-tracker records or restart Windows work.
