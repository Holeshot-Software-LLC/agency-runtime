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
  - docs/roadmap/issue-AR-120-normalized-workforce-recruitment-index.md
  - docs/roadmap/issue-AR-125-workforce-and-one-shot-evaluation.md
  - docs/roadmap/issue-AR-127-zcode-stop-rejection-shape.md
  - docs/roadmap/issue-AR-129-isolate-subprocess-environments.md
  - docs/roadmap/issue-AR-176-align-full-gate-contract-fixtures.md
  - docs/decisions/0223-retire-superseded-zcode-stop-checklist.md
  - docs/decisions/0222-retire-superseded-live-routing-contract.md
  - docs/roadmap/acceptance/evidence/AR-348-installed-delivery-20260905.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-404
branch: codex/ar127-oldest-first-reconciliation
evidence_commit: 7993046498114339b08a545f917514753047828a
minimum_ledger_commit: dfc844944ae7390e06ba1135986e156b6a872bb2
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/672
---

# AR-404 oldest-first backlog completion handoff

## Checkpoint

Owner priority: oldest first, one record, PR, merge, next; no routine approval
stops. Windows stays with the owner. Judge old agent proposals for relevance.
AR-115 is merged and retired. AR-119 reconciliation merged in PR #691 at
8b8b594e with its live obligations open. AR-120 reconciliation merged in
PR #692 at bc392228 with real index-quality gaps open. AR-125 reconciliation
merged in PR #693 at 79930464 with study/live requirements open. Current package:
retire AR-127's superseded checklist under ADR-0223, then inspect AR-129.

## Completed evidence

- AR-115: PR #690 merged at d9ea419b. Tracker #127 closed NOT_PLANNED at
  2026-09-05T23:47:12Z, read back. ADR-0222 supersedes ADR-0078's obsolete
  heuristic/six-field proposal. AR-119/125 own the surviving live outcome.
- AR-119: relevant incomplete umbrella, not a duplicate defect or a done item.
  Its August 18 matrix still has three proven and 42 unproven cells at 1bd7e37c.
  Reconcile stale status/capsule and R1 narrative without moving any cell,
  acceptance criterion, candidate, or founding rule. Tracker #132 stays open.
- AR-120: contracts, typed relationships, atomic snapshots and quarantine
  authority are present. 219 focused tests pass in 15.34s. Independent
  enrichment-review evidence, the approved discoverability baseline, and
  proposed contract/confusion/evaluation refresh remain missing. The weekly
  schedule is deliberate. #133 stays open with a bounded remaining plan.
- AR-125: configured/held-out matched selection, paired outcome lift and
  five-host live evidence are unfinished. 33 focused evaluator regressions
  pass (2.68s), not a live study. Old Windows/Linux candidate evidence is dated;
  the deferred AR-178 one-shot corpus is not restored. #138 remains open.
- AR-127: both output-shape repairs exist; ADR-0089 stays accepted. Retire its
  obsolete retry/unavailable/full-suite checklist, not the native wire contract.
  AR-135 owns current ZCode integration. Focused current-contract tests: 37 pass
  in 3.37s. The broader run has 133 pass/three known legacy failures (41.91s);
  AR-176 explicitly owns those removed public-tool/old retry assertions.
- Fresh external enumeration: 41 open trackers. Local unfinished: 140 records,
  41 mapped plus 99 legacy. Legacy was 104 before AR-148/149/152/323 completed
  and AR-139 retired. AR-115 changes mapped count, not the 99 legacy count.
  AR-127 local retirement leaves 139 unfinished (40 mapped plus 99 legacy);
  the remote count stays 41 until #151 is actually closed after merge.
- AR-115 focused routing/header/credential/records: 183 passed (19.11s).
  Fresh named spine: 1075 passed/three skips (68.74s). UI: 138 passed.
  Runtime/test/tool source unchanged from installed 0309f251.
- Prior PRs #687/#688/#689 delivered AR-348: both isolated criteria satisfied,
  413 focused passes/one skip, protected 184/184 mutation kills, exact installed
  source-byte identity, 45 installed hiring regression passes, eight-check
  deterministic smoke. #406 is closed. No five-host live pass was claimed.
- Earlier AR-404 batches completed AR-400..403, AR-405/271, AR-148/149/152/323/406
  and retired AR-132/167/169/267/139 with successor ownership. Frozen inventories
  and old failing receipts remain unchanged in canonical history.
- The requested Codex-only hook refresh returned exit 1: files installed,
  activation required, trust unverified, and a projection mismatch reported
  against the retained OpenClaw package. No fresh-session activation verified,
  no trust granted, no gateway restart. This is not an AR-119 live pass.

## Exact blocker

No blocker to the bounded AR-127 retirement and its PR/merge. The wider selected
run is not green; the three already-known obsolete fixture assertions are
recorded under AR-176 without changing or skipping them. Current ZCode live
proof remains AR-135's responsibility. AR-119/120/125 stay incomplete.
The ordinary-session staffing/header diagnosis remains set aside for backlog
order; the hook refresh did not resolve or waive it.

## Same-task continuity

Use one owned worktree and branch per item, never commit directly to main.
Substantive commit then immediate narrow docs(worklog) ledger; record the prior
merge in the following owned worktree. PR and merge before next disposition.
Preserve unrelated changes and historical evidence. Done requires isolated
acceptance; retirement needs explicit supersession/relevance, not fake verdicts.
At 50-percent telemetry make the smallest safe clean checkpoint, then continue.

## Next bounded work package

1. Publish AR-127 retirement, close #151 as NOT_PLANNED, read back state/count.
2. Review AR-129's subprocess environment boundary against current source;
   leave any Windows-specific execution for the owner.
3. Continue by original creation date and AR-number tie break. Retain genuine
   operator/dependency holds and move to the oldest actionable record.
   Skip Windows work; do not ask routine permission for the authorized PR loop.

## Verification

AR-119 record regressions: 93 passed (3.32s); metadata/strict docs pass for 1115
Markdown files; strict tracker parity passes for 397 mapped records. Matrix
rows, identity and founding vision are unchanged against d9ea419b.

Run metadata, policy availability, exact worklog, strict docs/tracker and diff
checks on each package. AR-120 adds the 219-case focused source check above;
AR-125 adds 33 and AR-127 adds 37 current-contract passes, with the wider three
legacy failures explicitly retained. No runtime/test/script/workflow changes.
Reuse the fresh unchanged receipts
above; no repeated six-minute mutation run for record-only reconciliation.
No new live inference, Windows execution, exhaustive corpus/coverage matrix,
cross-interpreter matrix or hosted workflow dispatch.

## Constraints

Do not create 99 trackers for exempt pre-tracker records. No specialist staffed
or native subagents spawned this turn; unreadable header evidence stays unverified.
Codex attended hook trust remains; Claude/Hermes/ZCode registration/enablement
is not fresh live proof. The live OpenClaw gateway retains its older package.
No credential creation, trust bypass, unmanaged gateway interruption, provider
policy change or exhaustive workflow dispatch is authorized by backlog cleanup.
