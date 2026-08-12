---
title: "AR-236 active recovery capsule"
status: active
category: roadmap
created: 2026-08-04
updated: 2026-08-12
tags: [handoff, cli, dashboard, parity, latency, observability, recovery]
related:
  - docs/roadmap/issue-AR-236-achieve-full-cli-dashboard-parity.md
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/analysis/2026-08-11-cli-vision-keep-list.md
  - README.md
  - agency_runtime/dashboard/dashboard-live.js
  - agency_runtime/dashboard/dashboard-render.js
  - agency_runtime/server/dashboard.py
  - tests/dashboard_ui.test.mjs
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-236
branch: codex/dashboard-vision-parity
evidence_commit: cfa67e4b0a912e24e748d885985467dddb8e4c84
minimum_ledger_commit: b1d2958a284b06cc182ed065798cc591207666b4
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/245
---

# AR-236 active recovery capsule

Restart state for the dashboard vision-parity work after the owner corrected
the scope boundary and Job B finished. The canonical issue owns acceptance;
this capsule owns the next bounded package.

## checkpoint

- PRs #271 and #273 completed Job B on `main` at `c7cf1d96`: Agency no
  longer drives host CLIs, plans work units, provisions worktrees, dispatches
  workers, or records a worker-pool ledger. Native hosts alone spawn and run.
- `codex/dashboard-vision-parity` rebased cleanly onto that commit. Its 21
  commits were rewritten; the clean post-Job-B recovery pair is
  `cfa67e4b` / `b1d2958a`. PR #270 remains draft and must not be merged as an
  inherited bundle merely because its earlier checks passed.
- The owner clarified the objective: keep the dashboard synchronized with the
  final vision. Prefer dashboard-only fixes, but a narrowly evidenced core,
  Store, CLI, adapter, or server correction is allowed when final `main`
  contradicts the vision or cannot support a truthful UI.
- The bounded dashboard truth package is implemented and verified in this
  checkpoint. It changes dashboard assets, UI tests, and user-facing README
  copy only; no core, Store, CLI, adapter, or dashboard-server code changed.

## completed-evidence

- The branch already removes delegation preference/mode/confidence controls,
  judge bypass, Route Lab work-unit/dependency graphs, and Agency-execution
  wording. Job B strengthens those deletions.
- Keep child inference budget, concurrency, and cache controls: they still
  bound host-started child routing in preflight.
- Shared latency evidence uses positive persisted durations, explicit
  attribution limits, nearest-rank p50/p95, and the pinned 15,000 ms budget.
- Shared specialist-distribution evidence uses decision and occurrence
  denominators, a 10,000-decision scan bound, active-roster context, top-ten
  concentration, and a bounded long tail. The owner observation is not
  hardcoded.
- Child delivery remains host-written, hash-verified evidence; staffing rows
  are not delivery proof. Rule-8 remains Store evidence about Agency
  withholding/blindness, never host publication proof. Wiring remains exact
  measured state with unsupported hosts explicitly not measured.
- Evidence requests are authenticated, view-scoped, source-separated, and off
  the hot poll. Empty, stale, and unavailable states are distinct and retain
  only source-specific last-good data.
- Settings no longer expose four invalid flat workforce model paths or the
  unenforced task/day hire caps. Four live workforce-change, warning, repair,
  and amend-overlap controls replace them, and the staffing-need limit now
  matches inference's hard maximum of 16.
- Hiring filters use status, type, and risk on the first request and preserve
  them while paging. Workforce and hiring refresh independently, and approval
  records an explicit 128-byte owner audit identity instead of a fabricated
  `dashboard-owner` value.
- Delegation-event rows show a child only when kind, worker ID, and native run
  ID are all observed. Recommendations and migrated partial rows never become
  executor identity; chart, table, and README copy stay source-neutral.
- Pre-Job-B browser QA covered populated, empty, partial-failure, cadence,
  accessibility, and 1440/1024/390 widths. Those results describe the rebased
  code but must be rerun after the post-Job-B rework.

## post-job-b-classification

Retain:

- latency, specialist distribution, child proof, Rule-8, wiring, the
  routing-intent retention guard, and removal of GET `/api/overview`, GET
  `/api/config`, and Route Lab delegation graphs;
- native-host ownership copy, staffing/specialist terminology, provider-builder
  model discovery, per-worker promotion readiness, and closest-worker detail.

Completed in the dashboard truth package:

- dead/live workforce settings, fallback-provider and Route Lab labels;
- hiring filter, paging, source-state, and approver-identity correctness;
- correlated execution identity and neutral delegation-event-row copy.

Rework before merge:

- replace latency causality claims with measured over-budget wording;
- make latency and selection endpoints require the active Store binding, so a
  configured DB-path change cannot present the process-frozen old Store as a
  fresh sample;
- remove broker/tests/docstring residues that still require the retired
  delegation graph. Do not restore the graph;
- retain the selection chart, but keep umbrella parity open until the shared
  projection has a CLI view or the owner narrows that acceptance.

Drop or defer:

- drop all Agency work-unit planning/execution UI and the stale workforce-only
  model helpers; do not add another readiness or per-worker duplicate panel;
- defer global consolidation review until `/api/workforce/duplicates` returns
  serialized, source-labelled rows with its real threshold contract;
- defer aggregate promotion queues and CLI hiring-list efficiency/filter work
  to their own bounded packages.

## exact-blocker

- A disabled broker explain currently still
  requires `delegation_graph` although the valid dashboard response removed it.
- Latency and selection handlers currently return an informational Store
  binding and keep reading the old process Store after a configured path
  change; their existing per-source stale states require a fail-closed 409.
- The post-Job-B browser QA and named fast spine have not yet run. PR #270's
  historical checks are not evidence for this newly reframed package.

## same-task-continuity

After every compaction, reread this capsule, the canonical AR-236 issue, and
`git status` before acting. Refresh `origin/main` before each package and merge
decision. Continue in this worktree.

## next-bounded-work-package

1. Create the dashboard truth package's substantive and ledger checkpoint.
2. Refresh main, then repair only the proven graph and active-Store-binding
   supporting contracts; do not revive Job B or broaden into owner diagnostics.
3. Re-evaluate specialist-distribution CLI parity, then run focused Python,
   populated/empty browser QA, and the named fast spine before any PR update.

## verification

~~~text
git rebase origin/main  # clean; 21 commits replayed onto c7cf1d96
node tests/dashboard_ui.test.mjs  # 132 passed
node --test --experimental-test-coverage ...  # 132 passed
# coverage: 96.75% lines, 86.39% branches, 95.45% functions
node --check <seven dashboard modules and UI test>  # passed
git diff --check  # passed
independent review  # no remaining High/Medium findings
~~~

## constraints

- Vision first, reachability second. Delete unsupported surface even if it
  still runs; preserve differently shaped host mechanisms when they provide
  the same required boundary.
- Never infer child delivery, host publication, execution identity, health, or
  causal latency attribution from an adjacent Agency row.
- Preserve Job B, refreshed main, AR-119 evidence, historical subjects, exact
  metric denominators, source freshness, bounds, and neutral empty states.
- Keep this capsule below 12 KiB and 180 lines; replace rather than append.
