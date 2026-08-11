---
title: "AR-236: Achieve full CLI and dashboard functional and presentational parity"
status: open
category: roadmap
created: 2026-08-04
updated: 2026-08-11
tags: [cli, dashboard, parity, ops, observability, analysis]
related:
  - docs/analysis/2026-08-04-cli-dashboard-parity.md
  - docs/roadmap/handoffs/issue-AR-236.md
  - README.md
  - docs/roadmap/issue-AR-123-workforce-cli-and-dashboard.md
  - docs/roadmap/issue-AR-153-complete-worker-detail-evidence.md
  - docs/roadmap/issue-AR-155-bound-dashboard-hiring-evidence.md
  - docs/roadmap/issue-AR-235-autonomous-gap-hiring-with-isolated-security-review.md
  - docs/roadmap/issue-AR-237-hiring-list-and-show-parity.md
  - agency_runtime/cli/parser.py
  - agency_runtime/cli/main.py
  - agency_runtime/cli/_render.py
  - agency_runtime/dashboard/dashboard-render.js
  - agency_runtime/dashboard/dashboard-actions.js
  - agency_runtime/server/http.py
  - agency_runtime/core/dashboard_operational.py
supersedes: []
superseded_by: null
type: issue
epic: operations
issue_id: AR-236
priority: p0
tracker_url: "https://github.com/Holeshot-Software-LLC/agency-runtime/issues/245"
depends_on: []
blocks: []
---

# AR-236: Achieve full CLI and dashboard functional and presentational parity

> **RESTATED 2026-08-11.** The August 4 inventory and ten-subissue plan below
> are retained as provenance, not as the current product contract. The vision
> subsequently retired Agency-authored host execution planning, mandatory
> delegation guidance, `unit_agent_plan`, and isolated delivery. Parity now
> means that every *vision-supported owner capability* has coherent CLI and
> dashboard projections; it does not mean copying developer, protocol, host
> lifecycle, or attended terminal commands into the browser. The first move is
> deletion or relabeling of UI that describes retired behavior, followed by
> source-backed latency, host-written child evidence, and selection-distribution
> observability. The current execution plan and exact restart state live in the
> [active recovery capsule](handoffs/issue-AR-236.md).

## Problem

The CLI and the dashboard do not have identical functionality parity.
Some operations are CLI-only, some are dashboard-only, and the
information density is asymmetric — the dashboard renders fields the
CLI does not print, and vice versa. The user requires that the
dashboard be a "pretty GUI" of the same capability surface the CLI
exposes, and the CLI be a "pretty terminal" of the same surface the
dashboard exposes. Both surfaces must expose the same operations; both
must present at parity in the medium that suits each.

## Current state

The full inventory is in
[`docs/analysis/2026-08-04-cli-dashboard-parity.md`](../analysis/2026-08-04-cli-dashboard-parity.md).
That analysis is the source of truth for the gap list and the
prioritized roadmap. The headline:

- CLI: ~50 top-level commands across 13 command groups
  (`parser.py:1477`).
- Dashboard: 6 views, 3 modals, 9 API actions
  (`dashboard-render.js`, `dashboard-actions.js`).
- The eval suite is confirmed developer-only and out of scope.
- "Pretty CLI" means `rich`-style card output with color-coded status,
  not a full-screen ncurses TUI.
- Phrase-typed confirmation (matching the dashboard's
  `confirmation-modal`) is the canonical pattern for destructive
  operations, replacing a `--yes` flag.

## Approach

Address the gap list as 10 focused sub-issues, each a separate PR that
touches both surfaces in the same commit set. The sub-issues are
prioritized in the analysis doc §"Top-priority gaps." Each sub-issue
opens its own AR when work on it starts; this AR is the umbrella that
records the parity goal, the analysis reference, and the closure of
each sub-issue.

Each sub-issue follows the slice pattern from
[AR-235](issue-AR-235-autonomous-gap-hiring-with-isolated-security-review.md):
- Thin scope per PR.
- Both surfaces updated in the same commit set.
- Validation gates: `docs_metadata.py --check`, `verify_docs.py`,
  `update_worklog.py --check`, `ruff check`, `ruff format --check`,
  the named fast spine, `git diff --check`.
- An ADR if the sub-issue introduces a durable architectural decision.
- A worklog row + matching `docs(worklog):` ledger commit.
- Open a PR when local validation is green.

The cross-cutting CLI presentation richness pass (item 10 in the
gap list) is its own sub-issue; it is not bundled with any functional
gap. It is the work that adds `rich`-style card output, color-coded
status, and live-watch to the CLI.

## Dependencies

- AR-123 (Add complete workforce CLI and live dashboard operations) —
  done. The original CLI + dashboard operations are in place; AR-236
  is the ongoing parity umbrella, not a re-do.
- AR-153 (Complete and bound worker-detail evidence) and
  AR-155 (Bound dashboard hiring evidence delivery) — open. They
  belong to AR-236's gap list; they may close as part of an AR-236
  sub-issue rather than standalone.
- AR-235 — open, parallel. AR-235 slice 1 introduces the
  `inference_profiles` module; AR-236 does not depend on it but the
  CLI presentation work in sub-issue 10 should consume any new
  structured-provider output the slice produces.
- `rich` (or equivalent) is the likely CLI presentation library; no
  decision recorded yet. If the sub-issue introduces a new
  presentation library, an ADR is required.

## Acceptance

The gap list in
[`docs/analysis/2026-08-04-cli-dashboard-parity.md`](../analysis/2026-08-04-cli-dashboard-parity.md) §"Top-priority gaps" becomes 10 sub-issues,
each of which is an AR or part of an existing AR. The closure of each
sub-issue is:

- [ ] **Sub-issue 1: Hiring list / show** — dashboard has a "Hiring
      cases" tab with list, detail, and approve; CLI `hiring list`
      and `hiring show` print the same fields the dashboard renders.
- [ ] **Sub-issue 2: Workforce promotion readiness** — both surfaces
      expose `verified_successes / required_successes` per worker and
      a "ready to promote" list. The dashboard already renders the
      card; the CLI must print the same fields.
- [ ] **Sub-issue 3: Workforce duplicates / consolidate** — dashboard
      has a "near-duplicates" mode filtered by
      `amend_overlap_threshold`; CLI `workforce duplicates` and
      `workforce consolidate` print the same workers the dashboard
      shows. The amend-first default from AR-235 surfaces here.
- [ ] **Sub-issue 4: Roster diff** — dashboard's snapshot panel has a
      side-by-side diff view that mirrors `agency roster diff`.
- [ ] **Sub-issue 5: Roster scans / candidate review** — full set of
      `agency roster scans` and `agency roster candidate-{audit,
      compare, findings, reject}` operations land in the dashboard's
      review queue.
- [ ] **Sub-issue 6: Roster sources and sync** — dashboard has a
      "Sources" panel with `source-add`, `source-list`, and `sync`
      that mirror the CLI surface.
- [ ] **Sub-issue 7: Doctor and DB stats** — dashboard surfaces
      `agency doctor` and `agency db-stats` as a small operator
      diagnostic view.
- [ ] **Sub-issue 8: Explain** — dashboard has an "Explain" action
      on the routing view that shows the same output as
      `agency explain`.
- [ ] **Sub-issue 9: Upgrade** — dashboard brings upgrade planning
      in as a multi-step flow. Note: this is a substantial sub-issue
      and may warrant its own AR with dedicated scoping.
- [ ] **Sub-issue 10: CLI presentation richness** — every existing
      CLI command grows a card-style output mode (e.g. `--card`),
      color-coded status matching the dashboard's CSS classes, and
      live-watch where the dashboard has live SSE updates. An ADR
      records the choice of presentation library (`rich` is the
      likely candidate).

## Acceptance for the umbrella AR

- [ ] Every gap item in the analysis doc has a sub-issue AR opened
      (or has been folded into an existing AR with a reciprocal
      `related` link).
- [ ] Each sub-issue's PR touches both surfaces in the same commit
      set.
- [ ] The CLI and dashboard expose the same operations, and the
      same fields per operation, end to end.
- [ ] The CLI's card-style output mode is at parity with the
      dashboard's card layout for the same operation.
- [ ] The dashboard has no operator-visible operation that the CLI
      cannot do, and the CLI has no operator-visible operation the
      dashboard cannot do.

## Out of scope (confirmed in the analysis)

- The `eval` suite (`agency eval *`) — developer surface, not
  operator. Confirmed by the user on 2026-08-04.
- Process lifecycle commands (`serve`, `dashboard`, `hook`, `mcp`,
  `codex-exec`, `run`) — not user-facing operations.
- Install / uninstall — host lifecycle, by design not in the
  dashboard.
