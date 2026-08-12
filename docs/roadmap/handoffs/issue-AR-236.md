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
evidence_commit: d94588906dfefe23d869eff19621d2c213f89de0
minimum_ledger_commit: 8d1a12132447730d2a674a98a025de8bacb7fac8
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
- The dashboard truth package is clean at `d9458890` / `8d1a1213`. The next
  supporting-contract slice is locally complete and verified: it changes only
  the smallest shared projection, CLI, broker, server, and test contracts that
  a truthful dashboard or matching CLI projection requires.

## completed-evidence

- The branch already removes delegation preference/mode/confidence controls,
  judge bypass, Route Lab work-unit/dependency graphs, and Agency-execution
  wording. Job B strengthens those deletions.
- Keep child inference budget, concurrency, and cache controls: they still
  bound host-started child routing in preflight.
- Shared latency evidence uses positive persisted durations, explicit timing
  limits, nearest-rank p50/p95, and the pinned 15,000 ms budget. Provider time
  comes from complete same-trace receipts; the remainder is explicitly derived
  as total minus provider time and is never labelled Agency timing.
- Shared specialist-distribution evidence uses decision and occurrence
  denominators, a 10,000-decision scan bound, active-roster context, top-ten
  concentration, and a bounded long tail. Dashboard and `agency evidence
  selections` now project the same Store result; no owner observation is
  hardcoded.
- Child delivery remains host-written, hash-verified evidence; staffing rows
  are not delivery proof. Rule-8 remains Store evidence about Agency
  withholding/blindness, never host publication proof. Wiring remains exact
  measured state with unsupported hosts explicitly not measured.
- Evidence requests are authenticated, view-scoped, source-separated, and off
  the hot poll. Metric reads fail 409 before touching a process-frozen Store
  after DB-path drift. Empty, stale, and unavailable states are distinct and
  retain only source-specific last-good data.
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
- Disabled broker explain, routing snapshots, lifecycle copy, and tests no
  longer require the retired delegation graph. The graph was not restored.
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

- rerun populated and fresh-empty real-browser QA after the post-Job-B changes;
- run the named fast spine and refresh `main` before the PR decision;
- keep umbrella parity open for the broader historical sub-issues below.

Drop or defer:

- drop all Agency work-unit planning/execution UI and the stale workforce-only
  model helpers; do not add another readiness or per-worker duplicate panel;
- defer global consolidation review until `/api/workforce/duplicates` returns
  serialized, source-labelled rows with its real threshold contract;
- defer aggregate promotion queues and CLI hiring-list efficiency/filter work
  to their own bounded packages.

## exact-blocker

- The post-Job-B real-browser QA and named fast spine have not yet run.
- PR #270 still points at the pre-rebase draft head; its historical checks are
  not evidence for this newly reframed package.

## same-task-continuity

After every compaction, reread this capsule, the canonical AR-236 issue, and
`git status` before acting. Refresh `origin/main` before each package and merge
decision. Continue in this worktree.

## next-bounded-work-package

1. Create the supporting-contract substantive and ledger checkpoint.
2. Refresh `main`, then run populated and fresh-empty real-browser QA.
3. Run the named fast spine, refresh `main` again, and update draft PR #270 only
   if the bounded package remains green and vision-aligned.

## verification

~~~text
git rebase origin/main  # clean; 21 commits replayed onto c7cf1d96
node tests/dashboard_ui.test.mjs  # 132 passed
node --test --experimental-test-coverage ...  # 132 passed
# coverage: 96.75% lines, 86.39% branches, 95.45% functions
node --check <seven dashboard modules and UI test>  # passed
git diff --check  # passed
focused latency/API/parser/graph tests  # 207 passed; final latency/API rerun 178 passed
node tests/dashboard_ui.test.mjs  # 133 passed after contract rename
independent review  # machine and visible attribution findings resolved
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
