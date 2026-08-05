---
title: "AR-246: Roster scans parity (sub-issue 5 of AR-236)"
status: done
category: roadmap
created: 2026-08-04
updated: 2026-08-04
tags: [cli, dashboard, parity, roster, scans, sub-issue]
related:
  - docs/roadmap/issue-AR-236-achieve-full-cli-dashboard-parity.md
  - agency_runtime/server/dashboard.py
  - agency_runtime/cli/roster_commands.py
supersedes: []
superseded_by: null
type: issue
epic: operations
issue_id: AR-246
priority: p1
tracker_url: "https://github.com/Holeshot-Software-LLC/agency-runtime/issues/255"
depends_on: []
blocks: []
---

# AR-246: Roster scans parity (sub-issue 5 of AR-236)

## Problem

The CLI has `agency roster scans` for listing immutable scan evidence. The
dashboard's review queue is partial.

## Approach

Add `GET /api/roster/scans` endpoint that calls `list_source_scans`.

## Acceptance

- [ ] `GET /api/roster/scans` returns scan evidence matching the CLI.
