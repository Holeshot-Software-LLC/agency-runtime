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
  - docs/analysis/2026-08-04-cli-dashboard-parity.md
  - README.md
  - agency_runtime/cli/evidence_commands.py
  - agency_runtime/core/store/evidence.py
  - agency_runtime/server/dashboard.py
  - agency_runtime/dashboard/index.html
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-236
branch: codex/dashboard-vision-parity
evidence_commit: 10093a1e0202119102de4b7b5a753988969d429f
minimum_ledger_commit: 10093a1e0202119102de4b7b5a753988969d429f
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/245
---

# AR-236 active recovery capsule

Bounded restart state for the approved CLI/dashboard vision-parity package.
The canonical issue owns acceptance; this capsule owns the next execution.

## checkpoint

- Owner approved local implementation and README correction on 2026-08-11.
  No GitHub issue, PR, push, or hosted workflow was authorized.
- Branch `codex/dashboard-vision-parity` was created from refreshed
  `origin/main`. It was fast-forwarded again to `10093a1e` after another
  worktree appended to AR-119. Product code is untouched; end telemetry reports
  25.4 percent remaining, so this local recovery checkpoint is required.
- AR-119 and `docs/worklog/README.md` are active cross-worktree conflict
  hotspots. Preserve their user-authored additions; fetch and rebase before any
  eventual push.
- The approved package is deletion-led: derive a keep-list from current vision,
  remove active UI for retired Job B behavior, then add evidence that answers
  current operator questions.

## completed-evidence

- Current contract: inference selects and staffs specialists; the native host
  alone decides whether and what to spawn. Agency must not author a host
  execution plan, tell the host to delegate, or block the parent until it does.
  AR-119 lines 54-65 explicitly retire product trials, `unit_agent_plan`, and
  isolated delivery. Commits `b456d0c1`, `7de64fe8`, `441b8850`, `40c608dc`,
  and `d9f6e6be` removed that machinery.
- README is stale at its opening explanation and ELI5 step 7: it still says
  every substantive unit is delegated and an undispatchable unit stops the
  turn. Rewrite it to describe staffing-only decomposition, host-owned
  execution, request-scoped cards, fail-open behavior, and host-written proof.
- Definitely dead dashboard controls: `delegation.mode`,
  `preferred_min_units`, `strongly_preferred_min_units`, and
  `strongly_preferred_min_confidence`. Their only behavior helper,
  `_delegation_strength`, has no production caller. Remove the four UI inputs.
  Keep legacy config parsing/fingerprinting for now so existing files do not
  break; full field deletion needs an explicit migration/version decision.
- Live controls that must stay: `child_inference_budget`,
  `child_inference_concurrency`, and `child_cache_ttl_seconds`. Preflight and
  the Store enforce them for host-spawned child routing. Relabel “unplanned
  child” as “native-child routing.”
- Live staffing bounds that must stay: `workforce.max_work_units`,
  `max_selected_per_unit`, `max_selected_total`, confidence, and margin. They
  bound inference staffing, not host execution. Relabel them as staffing units
  and workers per staffing unit.
- Audit `judge.confidence_bypass_threshold` before keeping it visible. Static
  search found config/wizard/doctor/tests but no current selection consumer.
  Do not delete compatibility plumbing on that fact alone.
- Route Lab still builds and renders `delegation_graph`, says units can run
  independently, and prompts for independent work units. Delete the graph
  projection and renderer; reword remaining unit display as staffing
  decomposition. “Execution host” should become target/compatibility host.
- Master/on-off copy incorrectly claims Agency starts or stops delegation.
  Replace it with routing, specialist-card injection, and evidence collection;
  native host spawning continues when Agency is bypassed.
- Overview SQLite delegation rows are useful history but not Rule-4 proof.
  Label them recorded native-child events. A separate projection must count
  only host-artifact-proven staffed children.
- New latency source is complete: decision duration is
  `routing_decisions.latency_ms`; per-call duration is
  `model_receipts.latency_ms`; `Store.get_routing_latencies()` already returns
  provider totals and call counts. CLI aggregation currently lives in
  `cli/evidence_commands.py` and must move to shared core code.
- Latency semantics are fixed: nearest-rank p50/p95, default 15000 ms budget,
  exclude non-positive decisions, equality passes, receipt total zero means
  unattributed legacy evidence, and group computed/cache sources separately.
- Owner requested a specialist-selection concentration chart after observing
  202 decisions across 39 selected specialists, with `code-reviewer` in over
  72 percent of decisions and the top ten holding 82 percent of selection
  occurrences. Treat those numbers as a prompt, not checked-in truth; compute
  the dashboard values from the active Store.
- Selection chart contract: horizontal top-specialist bars using decisions
  containing each specialist; show count plus percent of decisions. Separately
  show total decisions, distinct selected specialists, current active-roster
  size, total selection occurrences, and top-ten occurrence concentration.
  One decision may contain several specialists, so these denominators must be
  explicit and bars need not sum to 100 percent. Include a bounded long tail.
- Server-only parity endpoints with no frontend caller are roster diff/scans/
  sources, DB stats, workforce duplicates, and policy. Do not surface them just
  because AR-236 once listed them. Classify each against the vision keep-list;
  expose kept owner capabilities and delete redundant/dead routes.
- Vision-critical CLI evidence missing from the dashboard includes `evidence
  children`, `evidence rejections`, `evidence latency`, and `evidence wiring`.

## exact-blocker

- Product code/tests remain untouched. Metadata and policy checks pass;
  `verify_docs.py` has 11 inherited worklog/history errors on refreshed main.
- Tracker #245 may not match the locally reopened issue. External tracker
  mutation remains unauthorized; report the mismatch rather than hiding it.
- Installed hooks were reported stale during analysis. Do not judge new
  per-call attribution from live data until an explicitly approved install
  refresh and fresh decisions exist.
- Full removal of legacy config fields is not safe in the UI slice: existing
  configs and the context-policy fingerprint still carry them.

## same-task-continuity

Continue AR-236 in this branch. Re-read this capsule, current AR-236, README,
and latest AR-119; do not replay the stale August plan.

## next-bounded-work-package

1. Fetch/rebase the latest `origin/main`; inspect AR-119 and worklog conflicts.
2. Rewrite README opening, “How it works,” and dashboard description to current
   host-owned execution and evidence semantics.
3. Remove the four dead delegation-preference UI controls; relabel live child
   and staffing limits; confirm whether confidence-bypass is another dead UI.
4. Delete dashboard `delegation_graph`; correct Route Lab, master toggle,
   paused banner, and overview evidence labels. Preserve historical rows.
5. Extract a shared latency projection and add authenticated
   `GET /api/evidence/latency`. Do not add it to the 2.5-second `/api/live` poll;
   load on view/full refresh or a slower control cadence.
6. Add a shared selection-distribution projection and authenticated endpoint.
   Render the top bars, concentration metrics, and bounded long tail with exact
   denominators. Add children/rejections/wiring evidence in the same Assurance
   area only if the slice remains bounded.
7. Evaluate every frontend-unreachable endpoint against the vision keep-list.
8. Run focused Python and Node tests, the named fast spine, docs checks,
   telemetry, and two independent review passes. Create substantive and
   `docs(worklog):` ledger commits locally. Do not push without authorization.

## verification

~~~text
python scripts/context_handoff_status.py --json --threshold 50
python scripts/docs_metadata.py --check
python scripts/update_policy_availability.py --check
python scripts/update_worklog.py --check
python scripts/verify_docs.py
ruff check agency_runtime tests scripts
ruff format --check agency_runtime tests scripts
python -m pytest tests/test_evidence_latency.py tests/test_dashboard.py \
  tests/test_dashboard_auth_boundary_regression.py \
  tests/test_dashboard_transaction_refactors.py -q -W error
node --test tests/dashboard_ui.test.mjs
# Then run the AGENTS.md named fast Python production spine.
git diff --check
~~~

## constraints

- Preserve user work and historical evidence; no AR-119/worklog reconstruction.
- No push, PR, tracker mutation, hosted workflow, install, trust change, release,
  or publication without separate authorization.
- Use shared core projections so CLI and dashboard cannot drift on metric math.
- Keep latency/selection reads authenticated, bounded, metadata-only, and off
  the hot live poll. Empty evidence is unknown/no observations, never green.
- Do not confuse roster `context_mode=isolated_only` or resident-manager
  delivery states with the retired isolated product-delivery mode.
- Keep this capsule below 12 KiB and 180 lines; replace its bounded projection
  rather than appending a transcript.
