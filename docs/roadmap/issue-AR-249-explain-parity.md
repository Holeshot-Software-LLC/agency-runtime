---
title: "AR-249: Explain parity (sub-issue 8 of AR-236)"
status: open
category: roadmap
created: 2026-08-04
updated: 2026-08-04
tags: [cli, dashboard, parity, explain, routing, sub-issue]
related:
  - docs/roadmap/issue-AR-236-achieve-full-cli-dashboard-parity.md
  - agency_runtime/server/dashboard.py
  - agency_runtime/cli/roster_commands.py
supersedes: []
superseded_by: null
type: issue
epic: operations
issue_id: AR-249
priority: p1
tracker_url: "https://github.com/Holeshot-Software-LLC/agency-runtime/issues/258"
depends_on: []
blocks: []
---

# AR-249: Explain parity (sub-issue 8 of AR-236)

## Problem

The analysis doc called for an "Explain" action on the dashboard routing
view. Investigation shows the dashboard's route lab (`POST /api/route`)
already calls `explain_route` and returns the full selection-explain
receipt — the same output as `agency explain`.

## Current state

- The CLI `cmd_explain` calls `explain_route` and prints the receipt as JSON.
- The dashboard's `_handle_route_lab` (`POST /api/route`) also calls
  `explain_route` with the same arguments and returns the same receipt
  shape (`agency.selection_explain.v1`).
- Both surfaces produce identical output.

## Approach

No new endpoint is needed — parity is already achieved via the route lab.
The front-end "Route Lab" view already surfaces this as the routing
exploration surface. This sub-issue is closed by confirming the existing
parity rather than adding new code.

## Acceptance

- [x] The dashboard's route lab (`POST /api/route`) returns the same
      `explain_route` output as `agency explain --json`.
