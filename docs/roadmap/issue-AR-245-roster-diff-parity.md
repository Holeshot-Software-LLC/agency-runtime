---
title: "AR-245: Roster diff parity (sub-issue 4 of AR-236)"
status: done
category: roadmap
created: 2026-08-04
updated: 2026-08-12
tags: [cli, dashboard, parity, roster, sub-issue]
related:
  - docs/roadmap/issue-AR-236-achieve-full-cli-dashboard-parity.md
  - docs/analysis/2026-08-04-cli-dashboard-parity.md
  - agency_runtime/server/dashboard.py
  - agency_runtime/cli/roster_commands.py
supersedes: []
superseded_by: null
type: issue
epic: operations
issue_id: AR-245
priority: p1
tracker_url: "https://github.com/Holeshot-Software-LLC/agency-runtime/issues/254"
depends_on: []
blocks: []
---

# AR-245: Roster diff parity (sub-issue 4 of AR-236)

## Problem

The CLI has `agency roster diff` which creates a snapshot diff of
quarantined/approved candidates vs the active roster. The dashboard's
snapshot panel has no diff view.

## Approach

Add `GET /api/roster/diff` endpoint that calls `create_roster_diff` and
returns the same payload as the CLI.

## Acceptance

- [x] `GET /api/roster/diff` returns the roster diff matching the CLI output.
