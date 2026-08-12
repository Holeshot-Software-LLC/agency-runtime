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
evidence_commit: a78653cefa4b606d2fa048972459cc45040733e7
minimum_ledger_commit: da4ea3a4591eb0b0bbba75876719c780d3cf7687
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
  commits were rewritten; current HEAD before this recovery update is
  `da4ea3a4`. PR #270 remains draft and must not be merged as an inherited
  bundle merely because its earlier checks passed.
- The owner clarified the objective: keep the dashboard synchronized with the
  final vision. Prefer dashboard-only fixes, but a narrowly evidenced core,
  Store, CLI, adapter, or server correction is allowed when final `main`
  contradicts the vision or cannot support a truthful UI.
- Context telemetry reported 37.2 percent remaining, so this clean recovery
  pair is required before product edits and later live browser work.

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

Rework before merge:

- remove invalid `workforce.*_model` controls and their private discovery UI;
  remove unenforced `max_hires_per_task/day` controls; add the live
  `max_hires_per_turn`, `daily_hire_alert_threshold`,
  `hiring_repair_budget`, and `amend_overlap_threshold` controls;
- label `workforce.provider` as a fallback, and change Route Lab from
  `DETERMINISTIC + JUDGE` to `INFERENCE + VERIFICATION`;
- fix hiring apply/clear using the submitted filter on the first request, add
  the existing API's type filter, separate workforce and hiring source state,
  and collect explicit approver audit identity instead of
  `dashboard-owner`;
- render observed execution identity, not `recommended_agent`, and call the
  unfiltered historical source delegation-event rows rather than claiming
  every row is a native-child execution;
- replace latency causality claims with measured over-budget wording;
- make latency and selection endpoints require the active Store binding, so a
  configured DB-path change cannot present the process-frozen old Store as a
  fresh sample;
- remove broker/tests/docstring residues that still require the retired
  delegation graph. Do not restore the graph;
- retain the selection chart, but keep umbrella parity open until the shared
  projection has a CLI view or the owner narrows that acceptance;
- regenerate the worklog after the rebase and refresh AR-254 against the new
  canonical history.

Drop or defer:

- drop all Agency work-unit planning/execution UI and the stale workforce-only
  model helpers; do not add another readiness or per-worker duplicate panel;
- defer global consolidation review until `/api/workforce/duplicates` returns
  serialized, source-labelled rows with its real threshold contract;
- defer aggregate promotion queues and CLI hiring-list efficiency/filter work
  to their own bounded packages.

## exact-blocker

- The rebase rewrote 21 branch commits and introduced seven Job B commits from
  main. `update_worklog.py --check` and `verify_docs.py` correctly report stale
  and inaccurate rows until the canonical generator is rerun and this recovery
  pair is recorded.
- No textual conflict occurred, but graph requirements and generated history
  are semantic integration points. A disabled broker explain currently still
  requires `delegation_graph` although the valid dashboard response removed it.
- Latency and selection handlers currently return an informational Store
  binding and keep reading the old process Store after a configured path
  change; their existing per-source stale states require a fail-closed 409.
- PR #270's previous hosted static run failed; its historical passing focused
  evidence is not permission to merge the post-rebase, newly reframed branch.

## same-task-continuity

After every compaction, reread this capsule, the canonical AR-236 issue, and
`git status` before acting. Refresh `origin/main` before each package and merge
decision. Continue in this worktree.

## next-bounded-work-package

1. Regenerate and verify the canonical worklog; commit this post-Job-B recovery
   update and its ledger as a clean hard checkpoint.
2. Implement one dashboard truth package: dead/live settings, hiring filters
   and source state, approver identity, observed activity identity, and neutral
   source copy. Use dashboard files and UI tests only.
3. Independently review that package, run focused UI/config checks, update this
   capsule, and create its substantive/ledger checkpoint.
4. Then re-evaluate the retained evidence/server/CLI delta, repair only proven
   graph/parity/copy defects, and rerun focused Python, browser QA, and the named
   fast spine.

## verification

~~~text
git rebase origin/main  # clean; 21 commits replayed onto c7cf1d96
git diff --check  # passed immediately after rebase
context_handoff_status.py  # 37.2 percent remaining; checkpoint required
update_worklog.py --check  # expected stale after rewritten/new history
verify_docs.py  # expected 21 worklog/history errors before regeneration
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
