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
evidence_commit: 0596fd69dae319d61481a26ea5ea77cc342c37aa
minimum_ledger_commit: be7d44b3dd7bbcc88b474df54023fb2bcd41852a
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/245
---

# AR-236 active recovery capsule

Restart state for the approved dashboard vision-parity package. The canonical
issue owns acceptance; this capsule owns the next bounded execution slice.

## checkpoint

- AR-236 remains open. Product commit `0596fd69` is focused-verification clean;
  current-code browser QA and the named fast spine remain.
- The branch was rebased onto `b7832a03`, which merged the companion CLI
  vision re-scope. The four earlier AR-236 commits are now `29c3ce92`,
  `84e6a7d0`, `748490f4`, and `be7d44b3`.
- The rebase preserved the new CLI keep-list, AR-119 notes, worklog rows, host
  parity tests, and routing-intent declaration repair. AR-236 adds the missing
  retained-run orphan guard without duplicating the refreshed declaration.
- Local implementation and commits are authorized. Push, PR, tracker mutation,
  hosted workflows, installation, trust, and release actions are not. The owner
  explicitly requires a fresh check-in before any PR because other worktrees are
  active.

## completed-evidence

- README and dashboard copy now describe inference staffing, host-owned child
  execution, request-scoped card delivery, fail-open routing, and observable
  proof. The bundled roster count is 263.
- Retired delegation preference/mode/confidence settings, judge bypass, Route
  Lab dependency graph, work-unit planning UI, and the dashboard lifecycle
  import are gone. Compatibility-only config/data names remain internal.
- The companion CLI re-scope removed `delegate`, `run`, and `codex exec`; no
  corresponding dashboard execution control remains. Historical host-native
  child-event evidence remains because it observes rule-5 host behavior.
- Shared CLI/dashboard latency evidence uses positive persisted durations,
  nearest-rank p50/p95, a 15,000 ms budget, and attribution only when every
  provider call is timed. Empty or mixed evidence stays unknown.
- Store-backed specialist-selection evidence uses explicit decision and
  occurrence denominators, a 10,000-decision scan bound, active-roster context,
  top-ten concentration, bounded top rows, and a truthful long tail. The owner's
  202/39/72%/82% observation inspired the chart but is never hardcoded.
- Shared child proof scans only Claude/Codex host artifacts, follows no links,
  reads at most 4,096 bodies, visits at most 16,384 filesystem entries, reports
  incomplete candidate counts as lower bounds, and verifies card hashes before
  claiming delivery.
- Rule-8 evidence partitions bounded Store statuses into verifier-withheld and
  Agency-blind. It never infers host publication; CLI legacy aliases say so.
  Empty output is neutral, and invalid host/limit input fails before Store open.
- Wiring evidence resolves Claude's exact trusted `installed_plugins.json`
  binding rather than the newest cache mtime. Other hosts are explicitly
  `not_measured`; unavailable files never imply not-installed history.
- Owner-only `/api/evidence/{children,rejections,wiring}` endpoints are bounded
  and off `/api/live`. GET `/api/overview` and GET `/api/config` are removed;
  POST config stays. Route Lab rejects bad host/Store state before catalog work.
- Overview and Vision Evidence requests are view-scoped. Each source owns its
  fresh/stale/unavailable state and last-good data. Responses are schema and
  generation guarded; secondary 401 notices survive initial connection.
- Selection bars are semantic list items with CSP-safe native `<progress>`
  visuals. Dedicated concise live regions announce metric/Vision completion;
  dynamic proof text wraps at narrow widths.
- Endpoint keep-list: retain activity, roster diff/scans/sources, DB stats, and
  duplicate review for later owner UI slices; preserve hosts/inference/runtime/
  health/policy/search as service contracts; do not add panels merely because a
  route exists.

## exact-blocker

- Context telemetry was 21.6% remaining. Product commit `0596fd69` freezes the
  verified slice; this recovery/ledger pair completes the required clean local
  checkpoint before another live browser evaluation.
- An earlier source-browser pass proved populated metrics, responsive layout,
  populated/partial Vision states, and clean console before the final review
  fixes. It is useful discovery, not current-code acceptance. The current build
  still needs populated, empty, partial, narrow, accessibility, and request-
  cadence browser proof.
- The named fast Python spine, final docs gates, routing/decision evals, and QA
  fixture cleanup remain. Exhaustive coverage/compatibility and hosted workflows
  are not ordinary gates and are unauthorized.
- Metadata and policy checks pass. Refreshed main leaves `update_worklog.py`
  stale and `verify_docs.py` at 12 inherited history errors: one index-set
  mismatch covering seven main commits, seven inaccurate rows for those same
  commits, and four pre-existing ledger-path violations. No AR-236 row fails.
- Tracker #245 may not reflect this locally reopened scope. External changes
  remain unauthorized.

## same-task-continuity

After every compaction, reread this capsule, the canonical AR-236 issue, and
`git status` before acting. Continue in this worktree; do not restart the audit.

## next-bounded-work-package

1. Drop only the verified AR-236 rebase stash, never the unrelated main-worktree
   stash. Recheck telemetry immediately before source-dashboard browser QA.
2. Use the approved private temp fixture, never expose the token, and do not
   touch the installed service.
3. Prove populated, empty, partial-failure, responsive, accessibility, and
   request cadence. Metrics and Vision must remain off the 2.5-second hot poll.
4. Remove the temp harness/fixtures, run the named fast spine and docs gates,
   then update this capsule and canonical issue with exact evidence.
5. Create the final local recovery/ledger pair. Do not push; check with the
   owner before any PR or integration step.

## verification

~~~text
# Rebased focused product proof:
python -m pytest tests/test_child_delivery_evidence.py \
  tests/test_evidence_rejections.py tests/test_host_wiring_drift.py \
  tests/test_cli_parser_contract.py tests/test_dashboard.py \
  tests/test_routing_intent.py tests/test_coverage_closure_delegation_targets.py \
  tests/test_runtime_table_declarations.py tests/test_host_boundary_parity.py -q
# 278 passed
node --check agency_runtime/dashboard/{app,dashboard-core,dashboard-live,dashboard-render}.js
node tests/dashboard_ui.test.mjs
# 124 passed
uvx ruff check <changed Python files>
uvx ruff format --check <changed Python files>
# passed
git diff --check
# passed
~~~

## constraints

- Preserve refreshed main, historical subjects, AR-119, and Store evidence.
- Use shared projections so CLI and dashboard evidence math cannot drift.
- Evidence stays authenticated, bounded, metadata-only, source-labelled, and
  off the hot poll. Empty means no observation, never healthy.
- Staffing selections and historical `delegations` rows are not child-delivery
  proof; only hash-verified host artifacts prove pre-speech card delivery.
- Keep this capsule below 12 KiB and 180 lines; replace it rather than append.
