---
title: "AR-247: Roster sources parity (sub-issue 6 of AR-236)"
status: done
category: roadmap
created: 2026-08-04
updated: 2026-08-12
tags: [cli, dashboard, parity, roster, sources, sub-issue]
related:
  - docs/roadmap/issue-AR-236-achieve-full-cli-dashboard-parity.md
  - agency_runtime/server/dashboard.py
  - agency_runtime/cli/roster_commands.py
supersedes: []
superseded_by: null
type: issue
epic: operations
issue_id: AR-247
priority: p1
tracker_url: "https://github.com/Holeshot-Software-LLC/agency-runtime/issues/256"
depends_on: []
blocks: []
---

# AR-247: Roster sources parity (sub-issue 6 of AR-236)

## Problem

The CLI has `agency roster source-list` and `agency roster source-add`. The
dashboard has no Sources panel.

## Approach

Add `GET /api/roster/sources` endpoint that calls `list_agent_sources`.

## Acceptance

- [x] `GET /api/roster/sources` returns configured sources matching the CLI.
