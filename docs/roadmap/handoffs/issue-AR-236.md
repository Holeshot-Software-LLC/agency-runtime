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
evidence_commit: 6ce0c37ff84beaca244d436aa389eb5579d5c05b
minimum_ledger_commit: 419a888c10837f309122200ea34baec22dc79166
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
- The dashboard truth package is clean at `d9458890` / `8d1a1213`; the minimal
  supporting-contract slice is clean at `6ce0c37f` / `419a888c`. Both were
  independently reviewed with no unresolved High or Medium finding.

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
- Post-Job-B real-browser QA used the production CLI and real dashboard,
  Store, child-artifact, Rule-8, and wiring projections. The bounded populated
  Store fixture rendered 20 selection-bearing decisions, 13 distinct
  specialists, 35 occurrences, 91.4% top-ten concentration, correlated child
  identities only, and evidence-bounded latency attribution. No positive host
  proof was fabricated: isolated host homes produced zero verified cards,
  missing Claude wiring, and explicit not-measured states for other hosts.
- A fresh Store rendered selection `NO DATA`, latency `UNKNOWN`, current-empty
  workforce/hiring, zero-proof child caveats, Rule-8's non-health claim, and
  unknown wiring. Console/CSP checks were clean and 1440x900, 1024x768, and
  390x844 layouts had no document overflow.
- Path-only instrumentation around the real handlers proved metrics load once
  on Overview, proof sources load once on first Evidence entry, hot polling
  refetches none of the five, revisits reuse proof samples, and manual/global
  refreshes stay view-scoped. Ninety-one API log rows contained no token,
  authorization text, query, fragment, retired endpoint, or graph request.

## post-job-b-classification

- Retain latency, specialist distribution, child proof, Rule-8, wiring, native-
  host copy, live child-routing bounds, provider discovery, worker readiness,
  closest-worker detail, and the retired GET/config/graph removals.
- The truth package completes dead/live settings, hiring filters and paging,
  independent source state, approver identity, correlated execution identity,
  neutral event copy, browser QA, the fast spine, and routing/static gates.
- Drop all Agency work-unit planning/execution UI and stale workforce-only model
  helpers. Defer global consolidation review, aggregate promotion queues, and
  CLI hiring efficiency/filter work to bounded follow-ups. Keep AR-236 open.

## exact-blocker

- PR #270 still points at the pre-rebase draft head; its historical checks are
  not evidence for this newly reframed package.
- Decision conformance reaches the same inherited Windows evaluator baseline
  failure as `origin/main`: its forced venv Python fails executable-parent
  namespace trust for one OpenClaw test. The focused test passes when
  `AGENCY_CI_PYTHON` is unset; all relevant files are identical to `main`.

## same-task-continuity

After every compaction, reread this capsule, the canonical AR-236 issue, and
`git status` before acting. Refresh `origin/main` before each package and merge
decision. Continue in this worktree.

## next-bounded-work-package

1. Record this post-browser, post-fast-spine recovery checkpoint.
2. Refresh `main`, force-with-lease the rebased branch, and update draft PR
   #270 only if the vision-aligned delta remains unchanged.
3. Inspect fresh hosted checks, merge only when current evidence is green, and
   keep umbrella AR-236 open for its explicitly deferred historical sub-issues.

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
production-CLI browser QA  # populated + fresh-empty; 1440/1024/390; console/CSP clean
path-only real-handler cadence  # 91 safe rows; view-scoped evidence; no hot-poll refetch
named fast Python spine -q -W error  # 668 passed, 6 skipped
agency eval routing --json --no-details  # all gates passed; p95 4.957 ms
docs metadata/policy/worklog/verify_docs + full Ruff  # passed
agency eval decision-conformance  # inherited Windows launcher_identity baseline failure
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
