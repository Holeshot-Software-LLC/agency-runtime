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
evidence_commit: 3ee585fedd98b9aa0d7f49e3c240685a11288b28
minimum_ledger_commit: 6256035aca2e554d7109e39480ab6629ba523190
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/245
---

# AR-236 active recovery capsule

Restart state for the approved dashboard vision-parity package. The canonical
issue owns acceptance; this capsule owns the next bounded execution slice.

## checkpoint

- AR-236 remains open. PR #270 carries product commit `3ee585fe`; current-code
  browser and fast verification are complete for that bounded slice. Its first
  static CI run found only the release asset ceiling addressed below.
- The branch is rebased onto `9c4112c3`, preserving the companion CLI re-scope
  and later operator-policy changes. The four earlier AR-236 commits are now
  `50fe3e07`, `f4f35509`, `ebcc2eb9`, and `b448d637`.
- The rebase preserved the new CLI keep-list, AR-119 notes, worklog rows, host
  parity tests, and routing-intent declaration repair. AR-236 adds the missing
  retained-run orphan guard without duplicating the refreshed declaration.
- The owner subsequently authorized completing the open handoff work plus
  pushing, opening, and merging green PRs/worktrees to main while unattended.
  Check refreshed main before every checkpoint because another agent is active.

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
- A source-only real-browser pass proved the populated Store projection: 202
  selection-bearing decisions, 39 distinct specialists, 491 occurrences, a
  263-role active roster, 82.3% top-ten concentration, and `code-reviewer` at
  146 decisions/72.3%. Latency rendered p50 15.9 s, p95 25.9 s, provider p50
  9.54 s, Agency p50 6.36 s, and 1.00 calls/decision as over budget.
- Empty-browser evidence stayed neutral: selection was `NO DATA`, latency was
  `UNKNOWN` with dashes, child proof stated that no observed cards does not
  mean no children, Rule 8 said no matches is not a health claim, and all wiring
  outcomes remained unknown without install-history inference.
- An injected wiring-only failure made only wiring `STALE`, retained its five
  last-good rows, and left child delivery and Rule 8 `OBSERVED`; removing the
  sentinel restored all three sources. The clean populated/empty runs had no
  console errors, and recovery added none after the deliberate HTTP 400.
- At 1440x900, 1024x768, and 390x844 the document had no horizontal overflow;
  dynamic proof paths and selection rows did not clip. The chart is an
  accessible list with 15 list items and aria-hidden native progress visuals.
- Request logging proved latency/selections load once on initial Overview while
  Vision stays unloaded; hot polling did not refetch any of the five evidence
  endpoints. Evidence entry, proof refresh, Overview reentry, and global refresh
  changed only their intended source counts. Every log row was token-free.
- Four verified QA Python processes and four disposable fixture roots were
  removed, including the token-bearing stdout; no AR-236 process or temp root
  remains.
- Endpoint keep-list: retain activity, roster scans/sources, DB stats, and
  duplicate review for later owner UI slices. Do not wire roster diff until its
  mutating GET/full-manifest leak is replaced by explicit owner mutation plus a
  redacted read projection. Preserve service routes without gratuitous panels.

## exact-blocker

- PR #270's first hosted static lane failed because AR-236 grew the audited
  dashboard assets from 298,409 to 355,184 bytes beyond a 300 KiB guard. A
  documented 360 KiB ceiling in `634170c2` passes the exact 161-test workflow
  contract locally and the hosted workflow-contract step.
- The hosted rerun passed the Python spine and all mutations; 124/124 dashboard
  tests passed but coverage was 85.88% against 86%. Commit `8a5c2de2` now passes
  126/126 at 96.12% lines, 86.18% branches, and 94.00% functions.
- That run then passed the exact dashboard gate and all 83 decision mutations;
  only canonical documentation history failed. AR-254 commit `8d9e5058`
  rebuilds 772 worklog rows and exact-SHA-grandfathers four immutable mixed
  ledgers while keeping future enforcement strict. Docs and 142 focused tests
  pass locally. The hosted clone exposed environment-dependent `%h` width;
  `1694c326` now derives collision-checked eight-character IDs from full SHAs.
  The exact docs checks and 143 focused tests pass; push and rerun remain.
- Hosted CodeQL/dependency review passed. Manual exhaustive lanes remain skipped.
- Tracker #245 may not yet reflect the reopened umbrella and later UI scope.

## same-task-continuity

After every compaction, reread this capsule, the canonical AR-236 issue, and `git status` before acting. Continue in this worktree; do not restart the audit.

## next-bounded-work-package

1. Fetch/rebase `origin/main`; another agent may add or reframe dashboard scope.
2. Push AR-254, rerun PR #270 CI, and merge only when the aggregate is green.
3. Consolidate the active roster/workforce/ops audits into bounded owner-visible
   packages; repair unsafe contracts before adding any UI.
4. Preserve evidence boundaries, checkpoint each package in this capsule, and
   run proportionate focused/browser checks plus the named fast spine.

## verification

~~~text
Post-rebase focused product pytest: 278; new-base policy pytest: 26.
Post-rebase warning-strict Python spine: 668 passed, 6 skipped, 0 failed.
Hosted-failure contract reproduction after budget fix: 161 passed.
Exact dashboard coverage gate: 126 passed; 96.12/86.18/94.00 percent.
python -m agency_runtime.cli eval routing --json --no-details  # 39/39
Hosted decision conformance: 83/83 mutations killed.
uvx ruff check agency_runtime tests scripts  # passed
uvx ruff format --check agency_runtime tests scripts  # 651 files
python scripts/docs_metadata.py --check  # 676 files
python scripts/update_policy_availability.py --check  # passed
python scripts/update_worklog.py --check  # 772 commits; passed
python scripts/verify_docs.py  # 676 files; passed
git diff --check  # passed
~~~

## constraints

- Preserve refreshed main, historical subjects, AR-119, and Store evidence.
- Use shared projections so CLI and dashboard evidence math cannot drift.
- Evidence stays authenticated, bounded, metadata-only, source-labelled, and
  off the hot poll. Empty means no observation, never healthy.
- Staffing selections and historical `delegations` rows are not child-delivery
  proof; only hash-verified host artifacts prove pre-speech card delivery.
- Keep this capsule below 12 KiB and 180 lines; replace it rather than append.
