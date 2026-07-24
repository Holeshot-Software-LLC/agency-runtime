---
title: "Minify dashboard assets under the 256 KiB release budget"
status: active
category: worklog
created: 2026-07-23
updated: 2026-07-23
tags: [worklog, dashboard, release, AR-119, green-main]
related:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-117-parallelize-pr-verification.md
  - docs/roadmap/issue-AR-123-workforce-cli-and-dashboard.md
supersedes: []
superseded_by: null
type: worklog
commit: 9d68e7e
short: 9d68e7e
date: 2026-07-23
pr: null
related_issues:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-117-parallelize-pr-verification.md
---

# Worklog detail: fix(dashboard): minify shipped assets under the 256 KiB release budget

## Purpose

The merged `main` static gate (`quality-contracts` / "static quality,
documentation, and dashboard UI") was red because the packaged dashboard
assets totaled 275,892 bytes, exceeding the fixed 256 KiB / 262,144-byte
release budget asserted at `tests/test_release_packaging.py:70` by
13,748 bytes. PR #129 merged with this (and other) red jobs. This commit
repairs the shipped asset footprint so the static gate can go green
without raising or bypassing the budget, hiding assets, or removing
behavior.

## Approach

The ten budgeted files (`index.html`, `app.css`, `charts.js`, `app.js`,
`dashboard-actions.js`, `dashboard-config.js`, `dashboard-core.js`,
`dashboard-live.js`, `dashboard-render.js`, `package.json`) are all
hand-authored source; none are vendored bundles, sourcemaps, or generated
artifacts, and there is no JS build toolchain. The mass lived in
whitespace, blank lines, and per-line indentation, so a deterministic,
behavior-preserving reduction was applied directly to the shipped
sources:

- **CSS**: strip the two section-banner comments, collapse whitespace
  runs, and trim spaces around structural characters. All semicolons are
  preserved (a `;}`-collapse trial broke the
  `.button:disabled[aria-busy="true"], .button.is-pending { cursor: wait; }`
  assertion and was discarded).
- **HTML**: strip comments, collapse inline whitespace and blank lines,
  and collapse inter-tag whitespace. Attribute order and values are
  untouched.
- **JS (seven modules)**: strip comments and leading/trailing line
  whitespace and drop blank lines, with a string- and template-literal
  aware scanner. No identifier is renamed; the `charts.js` UMD wrapper,
  its `module.exports = charts`, and its `root.AgencyCharts = charts`
  writes remain intact so the `vm.Script` sandbox re-execution still
  succeeds.

Result: 275,892 B -> 240,565 B, **21.1 KiB of headroom**.

## Challenges encountered

- The dashboard UI suite (`tests/dashboard_ui.test.mjs`) reads these
  exact files via `readFileSync` and re-runs `charts.js` in a `vm.Script`
  sandbox, so the reduction had to preserve every asserted CSS/HTML
  substring and the UMD/module-export shape. Each assertion was checked
  against the minified output.
- A first CSS pass collapsed trailing semicolons before `}`, which broke
  the `cursor: wait;` substring assertion; that optimization was dropped.
- Telemetry (`scripts/context_handoff_status.py`) requires
  `CODEX_THREAD_ID` and is unavailable in a non-Codex shell; per
  AGENTS.md a conservative estimate is used and no empty continuation
  emission is produced.

## Decisions and alternatives

- In-place minification was chosen over a generator script plus a build
  step because the release contract reads the shipped files directly via
  `importlib.resources`, there is no JS toolchain, and a new build
  pipeline would expand the release surface. The transform is
  deterministic and reversible.
- The budget was not raised and no asset was hidden from measurement.
- Rejected: removing "dead" CSS/JS rules. The discovery confirmed no
  rule is provably dead, so such removals would risk behavior loss;
  whitespace/comment reduction alone provided ample headroom.

## Verification

- `node --test tests/dashboard_ui.test.mjs` -> **97 pass, 0 fail**.
- `python -m pytest tests/test_release_packaging.py tests/test_ci_sharding.py -q -W error`
  -> **20 passed**.
- Reproduced the budget via the exact `importlib.resources` path the
  test uses: total 240,565 B (< 262,144), headroom 21.1 KiB.
- `git diff --check` -> no whitespace errors.

## Follow-ups

- This unblocks only the static asset-budget check. The remaining
  Phase 0 work (Codex-hook event-set regression, `_RouteRequest`
  signature reconciliation, workforce contract validation, store/schema
  fixes, dashboard/MCP/delegation-activation reconciliation) is required
  before merged `main` CI is fully green and before any AR-119 live
  evaluation. Tracked under
  [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md).
- Future AR-123 dashboard-lifecycle edits can re-expand these files; the
  reduction is not a permanent format constraint.
