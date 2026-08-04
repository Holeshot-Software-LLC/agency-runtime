---
title: "AR-237: Hiring list and show parity (sub-issue 1 of AR-236)"
status: open
category: roadmap
created: 2026-08-04
updated: 2026-08-04
tags: [cli, dashboard, parity, hiring, ops, sub-issue]
related:
  - docs/roadmap/issue-AR-236-achieve-full-cli-dashboard-parity.md
  - docs/analysis/2026-08-04-cli-dashboard-parity.md
  - docs/roadmap/issue-AR-123-workforce-cli-and-dashboard.md
  - docs/roadmap/issue-AR-155-bound-dashboard-hiring-evidence.md
  - agency_runtime/cli/workforce_commands.py
  - agency_runtime/cli/parser.py
  - agency_runtime/cli/_render.py
  - agency_runtime/core/store/workforce.py
  - agency_runtime/server/dashboard.py
  - agency_runtime/dashboard/index.html
  - agency_runtime/dashboard/dashboard-render.js
  - agency_runtime/dashboard/dashboard-live.js
  - agency_runtime/dashboard/app.js
supersedes: []
superseded_by: null
type: issue
epic: operations
issue_id: AR-237
priority: p0
tracker_url: "https://github.com/Holeshot-Software-LLC/agency-runtime/issues/246"
depends_on:
  - AR-236
blocks: []
---

# AR-237: Hiring list and show parity (sub-issue 1 of AR-236)

## Problem

The dashboard can approve a hiring case via `POST /api/hiring/approve`, but
it cannot browse hiring cases at all. The CLI's `hiring list` and
`hiring show` exist but render tab-separated fields that omit the
`risk_tier` and the `contract_evidence` block the dashboard already
shows. The two surfaces are not at parity, and the dashboard's
existing hiring card cannot be reached without the same filter and
detail surface the CLI already exposes.

The
[AR-236 parity analysis](../analysis/2026-08-04-cli-dashboard-parity.md)
calls this the highest-impact, lowest-cost sub-issue of the ten-item
gap list.

## Current state

- The dashboard server's `GET /api/hiring` accepts `case_id`, `status`,
  and `type` filters in `agency_runtime/server/dashboard.py`. The
  detail lookup is via the `case_id` query parameter on the same
  endpoint.
- The dashboard's hiring section already renders a card grid with
  `proposed_slug`, `case_type`, `status`, `risk_tier`, `work_unit_id`,
  and a "Load full evidence" button that calls the same endpoint with
  `case_id`. There is no filter form for the hiring section yet.
- The CLI's `cmd_hiring_list` prints
  `id\tcase_type\tstatus\tproposed_slug\twork_unit_id` and
  `cmd_hiring_show` prints `id\tcase_type\tstatus\tproposed_slug`
  followed by `gap_evidence`, `duplicate_evidence`, `critic_evidence`,
  and `model_evidence` (no `contract_evidence`).
- The store's `HiringCaseSummary` projection in
  `agency_runtime/core/store/workforce.py` already carries
  `risk_tier`; the bounded projection is the source of truth for the
  collection.

## Approach

Implement the slice in one focused PR that touches both surfaces in
the same commit set.

1. **Server**: extend `_handle_hiring` to accept a `risk_tier` query
   filter and to return `risk_tier_counts` alongside
   `status_counts`. Map the store's `KeyError` on unknown `case_id` to
   `404 Not Found` (the existing path returns `400`, which the
   dashboard cannot distinguish from a malformed query). Extend
   `Store.get_hiring_cases_page_snapshot` to validate and apply
   `risk_tier` so the bounded filter is server-authoritative.
2. **Dashboard**: add a status + risk_tier filter form to the hiring
   section, wire the apply/clear buttons in `app.js`, route the
   intent through `live.applyHiringFilters` / `clearHiringFilters`,
   and have `fetchWorkforceCollections` pass the filter to the
   collection URL. The renderer shows the active filter summary in
   the count line and the panel status row.
3. **CLI**: add `agency_runtime/cli/_render.py` with a thin
   tab-separated card helper. Extend `cmd_hiring_list` and
   `cmd_hiring_show` to add the `risk_tier` column and the
   `contract_evidence` block respectively, and to render a card when
   `--card` is on. Default `--card` to on for a TTY stdout and off
   when piping, with `--no-card` always disabling and `--json` always
   winning.
4. **Tests**: focused tests for the new server endpoint filter and
   the 404 on unknown case; focused tests for the CLI card vs.
   `--json` output; a `tests/test_cli_render.py` module that locks
   the `_render.py` helper contract.

The CLI card style is intentionally a thin wrapper around
tab-separated text. Color, live-watch, and `rich` integration are
deferred to sub-issue 10 (CLI presentation richness) and a
dedicated ADR. The `rich` decision is not part of this slice.

## Dependencies

- AR-236 (parent umbrella). Reciprocal `related` link only; no
  `depends_on` until AR-236 reciprocates (the planning pair lesson).
- AR-123 (workforce CLI and dashboard) — done; the existing CLI and
  dashboard operations are the foundation.
- AR-155 (bound dashboard hiring evidence delivery) — open; the
  bounded projection this slice relies on landed in AR-155's
  evidence-bound path.

## Acceptance

- [ ] Dashboard's `GET /api/hiring` accepts `?status=` and
      `?risk_tier=`, returns the same bounded projection the CLI
      reads, and `404`s on an unknown `case_id`.
- [ ] Dashboard's hiring section has a status + risk_tier filter
      form. Applying the filter refreshes the count and the panel
      status row. Clearing the filter restores the unfiltered view.
- [ ] CLI's `hiring list` and `hiring show` print the same fields
      the dashboard renders (id, case_type, status, proposed_slug,
      risk_tier, work_unit_id; plus gap, duplicate, contract, critic,
      and model evidence in the show detail).
- [ ] CLI's `hiring list --card` and `hiring show --card` render a
      bounded card layout mirroring the dashboard's card. The card
      mode is on by default when stdout is a TTY, off by default
      when piping, and never on when `--json` is set.
- [ ] The new `agency_runtime/cli/_render.py` module is consumed by
      this slice and is ready for sub-issues 2-4 to grow on top of
      it.
- [ ] Focused tests pass: server endpoint tests
      (`tests/test_dashboard.py`), CLI output tests
      (`tests/test_workforce_cli.py`), and render module tests
      (`tests/test_cli_render.py`).
- [ ] No existing test weakened. Named fast spine (`test_inference_profiles`,
      `test_workforce_dynamic_hiring`, `test_workforce_hiring_contract`,
      `test_workforce_selection_safety`, `test_routing_correctness`) plus
      the new and existing workforce CLI / dashboard / render tests
      all pass under `-W error`.
- [ ] `ruff check`, `ruff format --check`, `docs_metadata --check`,
      `verify_docs`, `update_worklog --check`, and `git diff --check`
      all pass locally.
- [ ] PR opened against `main`. PR URL posted back to the operator
      for review and merge.

## Out of scope (per sub-issue 1)

- Sub-issues 2 through 10 from the AR-236 gap list. This slice
  delivers only the hiring list / show parity.
- The `rich` decision and the cross-cutting CLI presentation
  richness pass. A separate sub-issue and an ADR for the
  presentation library come later.
- Sub-issue 2 (workforce promotion readiness), sub-issue 3
  (workforce duplicates / consolidate), and the rest of the gap
  list.
- Confirmation modal changes beyond the existing approve flow.
- New hiring case creation, retraction, or amendment flows. This
  slice is read-only with the existing approve action.
- The dashboard's `hiring-list` panel ↔ worker-detail evidence
  blocks; the existing "Load full evidence" button continues to
  drive the per-case detail load through the same `case_id` query
  parameter.

## Decisions to record in the PR body

1. The new `GET /api/hiring` filter (`risk_tier`) was added in
   place rather than splitting the endpoint, because the existing
   `case_id` / `status` / `type` filters already use the same
   `_collection_query` helper. Splitting the URL family would
   duplicate validation and snapshot shape; one endpoint with
   `risk_tier` in the allowed filter set keeps the bounded
   projection contract intact.
2. The CLI's `--card` flag is tri-state via
   `argparse.BooleanOptionalAction`. `--card` forces on,
   `--no-card` forces off, neither is auto-detected from TTY, and
   `--json` always wins. This matches the cross-cutting decision
   the umbrella sub-issue 10 will reuse.
3. The card style is a thin wrapper around tab-separated text for
   this slice, not a `rich` integration. Color comes in a later
   sub-issue when the library is decided (sub-issue 10 + an ADR).
   Documented in the PR body so sub-issue 10 picks the library
   with full context.
