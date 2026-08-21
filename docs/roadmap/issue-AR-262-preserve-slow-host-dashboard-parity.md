---
title: "AR-262: Preserve slow host inspection parity in the dashboard"
status: in_progress
category: roadmap
created: 2026-08-21
updated: 2026-08-21
tags: [dashboard, hosts, parity, windows, AR-119]
related:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-236-achieve-full-cli-dashboard-parity.md
  - docs/roadmap/handoffs/issue-AR-119.md
  - agency_runtime/server/dashboard.py
  - tests/test_dashboard.py
  - tests/dashboard_ui.test.mjs
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: operations
issue_id: AR-262
priority: p0
tracker_url: null
depends_on: [AR-236]
blocks: [AR-119]
---

# AR-262: Preserve slow host inspection parity in the dashboard

## Problem

The authenticated dashboard can render a supported host as permanently stale
even though the same installed package and Store-backed CLI report a complete,
current host inspection. On this Windows machine Claude inspection routinely
finishes after the dashboard's two-second request deadline. Its successful
result was refreshable for only three seconds, while the control surface polls
every 15 seconds, so no ordinary UI poll could observe the completed value.

## Current state

- Exact-main merge `692a9257` was installed into Claude, Codex, ZCode, and the
  durable dashboard service with no service definition drift.
- CLI `status --json` and authenticated `GET /api/hosts` both report Claude as
  registered, native enabled, runtime on, and
  `enabled-runtime-unverified`.
- Before this repair, the rendered Hosts panel repeatedly reported Claude as
  `inspection-stale`, with registration and native enablement unknown.
- The workforce surface otherwise has exact CLI parity: 294 active workers,
  263 employees, 31 contractors, and 32 hiring records.
- The local candidate separates the three-second refresh horizon from a
  30-second last-good stale horizon. A normal rendered refresh now reports the
  same five host states as the CLI while background inspection remains bounded.
- Tracker creation is pending explicit authorization after the outward write
  was refused at the approval boundary; no tracker mutation occurred.

## Approach

Keep the two-second HTTP deadline and three-second refresh cadence. Add a
separate bounded stale horizon for the production host-inspection coordinator.
Once a successful inspection exists, requests past the refresh horizon start a
background refresh but may continue to use that last-good evidence for at most
30 seconds. When that stale horizon expires, preserve the existing fail-closed
behavior: clear actionable native fields and render `inspection-stale`.

Injected coordinators keep the old one-horizon default unless a distinct stale
horizon is explicitly supplied, so tests and callers do not silently receive a
longer actionability contract.

## Dependencies

- AR-236 owns CLI/dashboard functional parity.
- AR-119 requires the installed control plane to remain truthful while live
  host evidence is collected.
- Host mutation endpoints retain generation-bound controls and explicit cache
  invalidation after native state changes.

## Acceptance

- [x] A completed inspection remains current past its refresh horizon while a
      bounded background refresh is pending.
- [x] Evidence past the stale horizon still clears actionable fields and
      reports `inspection-stale`.
- [x] The production stale horizon bridges the 15-second control poll.
- [x] A rendered candidate dashboard reports Claude identically to CLI status
      after a normal refresh, without prewarming `/api/hosts`.
- [x] Workforce and hiring counts remain identical between CLI and dashboard.
- [x] Affected tests pass: 189 Python/hardening tests and 134 dashboard UI
      tests; the 802-test warning-strict production spine (20 skips), all 12
      proportional local gates, and focused Ruff checks are green.
- [ ] After explicit authorization, the tracker issue is linked and the
      candidate is merged through a non-draft pull request without hosted
      Actions.
- [ ] The merged exact-main dashboard is reinstalled and the same rendered
      parity check passes.
