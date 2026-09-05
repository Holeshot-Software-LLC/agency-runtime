---
title: "AR-404 oldest-first backlog completion handoff"
status: active
category: roadmap
created: 2026-09-05
updated: 2026-09-05
tags: [handoff, backlog, acceptance, delivery]
related:
  - docs/roadmap/issue-AR-404-evidence-led-backlog-completion.md
  - docs/roadmap/AR-404-oldest-first-reconciliation-20260905.md
  - docs/roadmap/AR-404-count-reconciliation-20260905.md
  - docs/roadmap/AR-404-backlog-dispositions-20260905.md
  - docs/roadmap/issue-AR-115-live-routing-trust.md
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/decisions/0222-retire-superseded-live-routing-contract.md
  - docs/roadmap/acceptance/evidence/AR-348-installed-delivery-20260905.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-404
branch: codex/ar115-retire-superseded-routing-contract
evidence_commit: e5662d912537ec6d6dfda5310577c1175e615128
minimum_ledger_commit: e5662d912537ec6d6dfda5310577c1175e615128
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/672
---

# AR-404 oldest-first backlog completion handoff

## Checkpoint

The owner changed priority: clean the backlog oldest first, one record at a
time, PR, merge, then next, without routine approval pauses. Windows stays with
the owner. Judge agent-written proposals for current relevance; do not blindly
implement them. Current work: AR-115 retirement, not live-runtime certification.
The ordinary-session staffing/header diagnosis is set aside per owner request.
Main e5662d91 is clean and includes the preceding AR-348 delivery.

## Completed evidence

- AR-115 is the oldest unfinished record. It still specifies heuristic
  specialist fallback, a six-line Why/How header, and obsolete routine full-CI
  gates. ADR-0118, implemented AR-357, and ADR-0105 already replaced those
  contracts. ADR-0222 supersedes ADR-0078 and retires AR-115 as wont_do, not done.
  Original checked/unchecked gates remain historical and unchanged.
- AR-119 explicitly absorbs the surviving ordinary live selection/header
  obligation; AR-125 retains independent selection/outcome and native evidence.
  Both stay open. The current credential-unset/unstaffed/unverified session is
  not a pass. No implementation, configuration, credential or trust change.
- Fresh AR-115 focused routing/header/credential/resident-manager and document/
  tracker package: 183 passed in 19.11s. Fresh named fast spine: 1075 passed,
  three existing skips in 68.74s. Source is unchanged from installed 0309f251.
- Starting this oldest-first pass: 42 actual open trackers plus 99 unfinished
  legacy local records (141 total), not 141 demonstrated defects. The earlier
  legacy population was 104: AR-148/149/152/323 completed and AR-139 retired.
  AR-115 retirement reduces local unfinished to 140 (41 mapped plus 99 legacy).
  Tracker #127 remains open until this package merges; do not claim closure yet.
- Prior PRs #687/#688/#689 delivered AR-348: two unchanged satisfied criteria,
  413 focused passes/one skip, 1075 spine passes/three skips, 138 UI cases,
  routing pass, protected 184/184 mutation kills with source unchanged.
  Exact immutable installed 0309f251: every tracked runtime byte matches,
  45 installed hiring regressions pass and deterministic smoke passes 8/8.
  Tracker #406 (AR-348) closed, read back. Earlier failed umask receipts remain.
- Prior AR-404 batches completed AR-400..403, AR-405/271, AR-148/149/152/323/406
  and retired AR-132/167/169/267/139 with successor ownership. The frozen original
  inventory is not rewritten. Full details stay in canonical issues/evidence.

## Exact blocker

No blocker to the scoped AR-115 record reconciliation. It still needs its
substantive/ledger checkpoint, PR/merge, and authorized #127 not-planned closure.
Retirement must not be misreported as repaired ordinary staffing or accepted
live evidence. AR-119 remains an unfinished umbrella with its own dependencies.
Do not force an umbrella complete to advance to the next oldest actionable item.

## Same-task continuity

Work in the named owned branch/worktree; never commit directly to main.
Substantive commit then immediately narrow docs(worklog) ledger. Include exact
merge history in the following owned worktree. Create one PR per disposition
and merge before starting the next record. Preserve other workers' changes.
Completed issues require real isolated acceptance; wont_do needs explicit
supersession/relevance reasoning, not fabricated acceptance verdicts.
At the 50-percent telemetry checkpoint, commit the smallest safe recovery pair
and continue the same task. No empty commit or automatic task transfer.

## Next bounded work package

1. Publish AR-115 retirement, close #127 as not planned, and read back parity.
2. Review AR-119 next against its current nine-rule/host contract, not its large
   superseded execution history. Retain unresolved dependent/live obligations.
3. Then AR-120; thereafter continue by original creation date and AR-number tie
   break. Skip Windows work, record exact operator/dependency holds, and move
   to the next actionable record without requesting routine approval.

## Verification

Current runtime/test/tool source is unchanged from merged and installed
0309f251; new tests above exercise existing behavior only. No new live inference,
Windows execution, exhaustive corpus/coverage or cross-interpreter matrix.
Prior installed eight-check smoke is contract-only, not five live sessions.
Run metadata, policy availability, exact worklog, strict docs/tracker and diff
checks on each completed record package. Do not repeat six-minute unchanged
mutation runs solely for a documentation-only retirement.

## Constraints

Do not create 99 trackers for exempt historical records. Keep acceptance
failures and old subjects faithful. No specialist was staffed this turn; no
native subagents were spawned. Header evidence is unavailable, not guessed.
Codex files are refreshed but attended hook trust remains; Claude/Hermes/ZCode
are registered/enabled, not fresh-live proven. OpenClaw remains on its prior
projection because its running gateway must not be stopped or restarted.
The previous install restarted the managed dashboard and reported consented
repair of fourteen Claude entries; no new install is part of this docs slice.
No credential creation, trust bypass, unmanaged gateway interruption, provider
policy change or exhaustive workflow dispatch is authorized by backlog cleanup.
