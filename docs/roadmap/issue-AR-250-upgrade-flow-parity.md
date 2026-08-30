---
title: "AR-250: Upgrade flow parity (sub-issue 9 of AR-236)"
status: open
category: roadmap
created: 2026-08-04
updated: 2026-08-12
tags: [cli, dashboard, parity, upgrade, sub-issue]
related:
  - docs/roadmap/issue-AR-236-achieve-full-cli-dashboard-parity.md
  - agency_runtime/server/dashboard.py
  - agency_runtime/cli/upgrade_commands.py
supersedes: []
superseded_by: null
type: issue
epic: operations
issue_id: AR-250
priority: p2
tracker_url: "https://github.com/Holeshot-Software-LLC/agency-runtime/issues/259"
depends_on: []
blocks: []
---

# AR-250: Upgrade flow parity (sub-issue 9 of AR-236)

## Problem

The CLI has `agency upgrade` (plan / run / list). The dashboard has
`GET /api/update` which returns the update snapshot but does not expose the
plan/run/list operations as a multi-step flow.

## Current state

- `GET /api/update` returns `dashboard_update_snapshot` (cached release/main
  identity with bounded refreshes).
- The CLI `cmd_upgrade` supports `--plan`, `--run`, and `--list` subcommands.
- The dashboard surfaces the update status but not the plan/run actions.

## Approach

This is the largest sub-issue. The analysis doc notes it "may warrant its
own AR with dedicated scoping." The current dashboard surfaces update
availability; the multi-step plan/run flow is deferred to a dedicated
follow-up because it involves destructive host-level operations that need
the same phrase-typed confirmation pattern as other destructive ops, plus
host-canary validation.

## Acceptance

- [x] `GET /api/update` surfaces the same update snapshot the CLI checks.
- [ ] The multi-step plan/run upgrade flow is deferred to a dedicated AR.
