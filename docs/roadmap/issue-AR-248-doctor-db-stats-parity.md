---
title: "AR-248: Doctor and DB stats parity (sub-issue 7 of AR-236)"
status: open
category: roadmap
created: 2026-08-04
updated: 2026-08-04
tags: [cli, dashboard, parity, doctor, db-stats, sub-issue]
related:
  - docs/roadmap/issue-AR-236-achieve-full-cli-dashboard-parity.md
  - agency_runtime/server/dashboard.py
  - agency_runtime/cli/roster_commands.py
  - agency_runtime/cli/config_commands.py
supersedes: []
superseded_by: null
type: issue
epic: operations
issue_id: AR-248
priority: p2
tracker_url: "https://github.com/Holeshot-Software-LLC/agency-runtime/issues/257"
depends_on: []
blocks: []
---

# AR-248: Doctor and DB stats parity (sub-issue 7 of AR-236)

## Problem

The CLI has `agency db-stats` and `agency doctor`. The dashboard has no
diagnostic view.

## Approach

Add `GET /api/db-stats` endpoint that calls `database_stats`. The doctor
diagnostic is deferred (it involves provider reachability checks).

## Acceptance

- [ ] `GET /api/db-stats` returns SQLite stats matching the CLI.
