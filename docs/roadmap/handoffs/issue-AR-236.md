---
title: "AR-236 active recovery capsule"
status: active
category: roadmap
created: 2026-08-04
updated: 2026-08-11
tags: [handoff, cli, dashboard, parity, latency, observability, recovery]
related:
  - docs/roadmap/issue-AR-236-achieve-full-cli-dashboard-parity.md
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - README.md
  - agency_runtime/core/routing_latency.py
  - agency_runtime/core/selection_distribution.py
  - agency_runtime/server/dashboard.py
  - agency_runtime/dashboard/dashboard-live.js
  - agency_runtime/dashboard/dashboard-render.js
  - tests/test_evidence_latency.py
  - tests/test_specialist_selection_distribution.py
  - tests/dashboard_ui.test.mjs
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-236
branch: codex/dashboard-vision-parity
evidence_commit: 6d77819b5a326ee50536997bacc05bdbb26802be
minimum_ledger_commit: 9c02271e763debe2c62e2621a8708cd8cef3ff9e
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/245
---

# AR-236 active recovery capsule

Restart state for the approved dashboard vision-parity package. The canonical
issue owns acceptance; this capsule owns the next bounded execution slice.

## checkpoint

- This checkpoint contains the README rewrite, dead-setting and stale graph
  removal, shared routing-latency evidence, and specialist-selection
  distribution evidence. AR-236 remains open.
- Agency now describes its supported contract as inference-based staffing and
  request-scoped specialist-card delivery. The native host owns execution and
  child lifecycle; Agency records only evidence it can actually observe.
- At capture, before the new substantive/ledger pair, the branch was two
  commits ahead of and six behind `origin/main`. Do not push or resume editing
  before fetching and rebasing the clean checkpoint.
- AR-119 and `docs/worklog/README.md` are active cross-worktree conflict
  points. Preserve the additions from `origin/main`; never reconstruct them
  from this capsule.
- Local implementation was authorized. Push, PR, tracker mutation, hosted
  workflow, installation, trust changes, and release actions were not.

## completed-evidence

- README opening, architecture, behavior, host matrix, dashboard description,
  and ELI5 material now describe staffing-only inference, host-owned execution,
  fail-open behavior, and host-written proof. The bundled roster count is 263.
- Dashboard settings no longer expose retired delegation mode/preference/
  confidence fields or the unused judge confidence-bypass threshold. Legacy
  config parsing and fingerprint fields remain for compatibility.
- Route Lab no longer builds or renders `delegation_graph`; retired dependency
  graph/work-unit UI and CSS are gone. Master, paused, overview, evidence, and
  settings copy distinguish Agency staffing from native-child activity.
- Live child safeguards (`child_inference_budget`, concurrency, and cache TTL)
  and workforce staffing bounds remain, with labels matching their current
  purpose. Historical API/data field names named `delegations` remain where
  changing them would be a compatibility migration.
- `core/routing_latency.py` is the shared projection for CLI and dashboard.
  It uses nearest-rank p50/p95, a default 15,000 ms budget, excludes
  non-positive decisions, treats p95 equality as within budget, orders the
  slowest observations descending, and separates computed/cache sources.
- Provider-versus-Agency attribution is emitted only when every provider call
  has positive timed evidence. Mixed legacy/current receipts expose explicit
  unknown-call counts instead of inventing a split.
- Authenticated `GET /api/evidence/latency` returns bounded v1 evidence. The
  Overview panel shows count, p50, p95, max, budget status, attribution, source
  rows, slowest observations, and a truthful unknown state.
- `core/selection_distribution.py` and its Store query project the newest
  10,000 selection-bearing decisions. Authenticated
  `GET /api/evidence/selections` returns explicit decision and occurrence
  denominators, current active-roster size, top-ten occurrence concentration,
  bounded top specialists, long tail, scan limit, and truncation state.
- Overview renders selection summaries and horizontal bars from Store data.
  The owner-provided 202/39/72%/82% observation inspired the chart but is not
  hardcoded. Long-tail decision count is the unique count of decisions with at
  least one tail specialist.
- Both evidence requests use one dedicated Overview request scope after
  initial/manual refresh and on entering Overview. They stay out of `/api/live`
  and the 2.5-second poll; partial failures retain last-good data and show stale
  state. Responses are schema-validated and view-generation guarded.

## exact-blocker

- The vision keep-list audit of frontend-unreachable server endpoints is not
  complete. Do not add panels solely because an endpoint exists.
- CLI evidence for children, rejections, and wiring still lacks equivalent
  dashboard presentation. This slice added latency and selections only.
- No real-browser visual/accessibility QA has been performed on the new
  Overview panels. The named fast Python production spine and two final review
  passes have not run.
- Documentation metadata and policy-availability checks pass. `update_worklog`
  reports the baseline index as stale, and `verify_docs.py` repeats the same 11
  inherited worklog/history errors recorded at the prior checkpoint: seven
  index mismatch/inaccuracy errors and four ledger-path violations.
- The full warning-strict corpus, coverage shards, compatibility matrix, live
  install canary, and hosted workflows were not requested and did not run.
- Tracker #245 may not reflect the locally reopened scope. External tracker
  mutation remains unauthorized.

## same-task-continuity

Continue AR-236 on this branch. Start by reading this capsule and the canonical
issue, then fetch/rebase `origin/main` before changing files. Resolve AR-119 and
worklog conflicts in favor of refreshed main plus this checkpoint's exact row.

## next-bounded-work-package

1. Confirm the worktree is clean, fetch, and rebase onto `origin/main`; rerun
   the focused tests if conflicts touch product code or tests.
2. Run a real-browser visual/accessibility pass on Overview latency and
   selection evidence: populated, empty, partial-failure, narrow viewport, and
   navigation/refresh cases.
3. Classify every frontend-unreachable dashboard endpoint against the current
   vision. Record keep/delete/defer with owner question and source of truth.
4. Add children, rejections, and wiring dashboard evidence only if the keep-list
   confirms them and the next slice remains bounded.
5. Run the named fast spine, docs gates, `git diff --check`, and at most two
   independent reviews. Fix only findings that invalidate this outcome.
6. Update this capsule and canonical issue, then create the next local
   substantive/ledger pair. Do not push without separate authorization.

## verification

~~~text
# Passed at this checkpoint:
uvx ruff check <changed Python files>
uvx ruff format --check <changed Python files>
python -m pytest tests/test_evidence_latency.py \
  tests/test_specialist_selection_distribution.py tests/test_dashboard.py \
  -k "latency or selection_distribution or metric_evidence or route_lab" -q
# 36 passed, 129 deselected
node --check agency_runtime/dashboard/{app,dashboard-live,dashboard-render,charts}.js
node tests/dashboard_ui.test.mjs
# 112 passed, 0 failed
python scripts/docs_metadata.py --check
# checked 674 Markdown documents
python scripts/update_policy_availability.py --check
# passed
git diff --check
# passed (line-ending normalization warnings only)

# Baseline documentation failures, to re-evaluate after rebase:
python scripts/update_worklog.py --check
# worklog index is stale
python scripts/verify_docs.py
# same 11 inherited worklog/history errors as the prior checkpoint

# Still required after the rebase/final bounded slice:
# Then run the AGENTS.md named fast Python production spine.
node --test tests/dashboard_ui.test.mjs
~~~

## constraints

- Preserve user work, historical subjects, AR-119 additions, and Store evidence.
- Use shared core projections so CLI and dashboard metric math cannot drift.
- Keep evidence authenticated, bounded, metadata-only, and off the hot poll.
  Empty evidence is unknown/no observations, never healthy or zero latency.
- Do not infer native-child execution from staffing selections or historical
  `delegations` rows; use host-authored artifacts when execution proof matters.
- Keep this capsule below 12 KiB and 180 lines; replace it rather than append.
