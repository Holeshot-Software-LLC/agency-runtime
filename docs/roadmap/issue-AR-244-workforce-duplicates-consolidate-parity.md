---
title: "AR-244: Workforce duplicates and consolidate parity (sub-issue 3 of AR-236)"
status: done
category: roadmap
created: 2026-08-04
updated: 2026-08-12
tags: [cli, dashboard, parity, workforce, duplicates, sub-issue]
related:
  - docs/roadmap/issue-AR-236-achieve-full-cli-dashboard-parity.md
  - docs/analysis/2026-08-04-cli-dashboard-parity.md
  - docs/roadmap/issue-AR-240-amend-first-staffing-default.md
  - agency_runtime/server/dashboard.py
  - agency_runtime/cli/workforce_commands.py
supersedes: []
superseded_by: null
type: issue
epic: operations
issue_id: AR-244
priority: p1
tracker_url: "https://github.com/Holeshot-Software-LLC/agency-runtime/issues/253"
depends_on: []
blocks: []
---

# AR-244: Workforce duplicates and consolidate parity (sub-issue 3 of AR-236)

## Problem

The CLI has `workforce duplicates` and `workforce consolidate` commands that
list near-duplicate workers and recommend consolidation. The dashboard has
no equivalent view. The dashboard's roster view has a filter form and search
but no "near-duplicates" mode.

## Current state

- The CLI `cmd_workforce_duplicates` and `cmd_workforce_consolidate` call
  `nearest_workers` and `consolidation_candidates` from
  `agency_runtime/core/workforce/comparison.py`.
- The dashboard server has no `/api/workforce/duplicates` endpoint.
- The `amend_overlap_threshold` from AR-240 is available for filtering.

## Approach

Add a `GET /api/workforce/duplicates` endpoint to the dashboard server that
calls `consolidation_candidates` and returns the same payload structure the
CLI's `workforce consolidate --json` emits. This gives the dashboard the
data to render a "near-duplicates" panel. The front-end rendering is a
follow-up; this slice delivers the server-side parity.

## Acceptance

- [x] `GET /api/workforce/duplicates` returns the consolidation candidates
      payload (workforce_count, contract_fingerprint, authority,
      automatic_mutation, candidates) matching the CLI's
      `workforce consolidate --json` output.
- [x] The endpoint requires owner auth (read-side but workforce-sensitive).
