---
title: "AR-151: Align Route Lab host eligibility with the server"
status: open
category: roadmap
created: 2026-07-26
updated: 2026-09-07
tags: [dashboard, routing, hosts, traceability]
related:
  - docs/decisions/0095-complete-paginated-dashboard-collections.md
  - docs/roadmap/issue-AR-137-complete-dashboard-collections.md
  - docs/roadmap/issue-AR-404-evidence-led-backlog-completion.md
  - docs/roadmap/issue-AR-176-align-full-gate-contract-fixtures.md
  - docs/roadmap/acceptance/evidence/AR-151-host-eligibility-20260907.md
  - docs/decisions/0117-unify-owner-control-authority.md
  - docs/decisions/0118-require-inference-owned-staffing.md
  - docs/worklog/README.md
  - agency_runtime/dashboard/dashboard-render.js
  - agency_runtime/server/dashboard.py
supersedes: []
superseded_by: null
type: issue
epic: dashboard
issue_id: AR-151
priority: p1
tracker_url: null
depends_on: []
blocks: []
---

# AR-151: Align Route Lab host eligibility with the server

## Problem

The browser keeps the first duplicate host and can enable Route Lab while the
server classifies duplicate or oversized inventories as ambiguous and rejects
the same request. The UI can therefore advertise an action it cannot perform.

## Current state

September 7 review confirms 6a3bdaa's bounded duplicate rejection remains in
both the production renderer and authoritative POST handler. Duplicate identities
are excluded individually; a different unambiguous verified host remains usable.
More than ten inventory rows disable the entire Route Lab host selection.
The original first-duplicate behavior is historical, not current code.

Thirteen new direct GET → production renderer/action controller → POST contract
cases pass (13.45s), including all five execution hosts, normalized duplicate
identities, the exact size bound and forged submissions for excluded hosts.
Current core dashboard/auth/transaction suite: 193 pass (40.75s); UI: 176 pass
at 96.93/86.70/95.71, above unchanged 95/86/93 floors. No product change.

The broader six-module dashboard run is not green: 265 pass, nine fail (53.81s).
All nine reproduce on unchanged main 460f319b (4.81s). Seven denial cases use
an owner token despite ADR-0117; one cache fixture omits its stale deadline;
one inference fixture treats the configured legacy chain as unconfigured.
These nine fixture mismatches are repaired without runtime changes: broker
denials retain 403/no-dispatch, fresh cache evidence has both deadlines, and
optional local acceleration is distinguished from a declared judge chain.
The corrected six-module suite passes 274 in 52.54s; focused nine pass in 4.71s.
The named Python spine passes 1085 with three existing skips in 68.98s; routing,
Ruff and diff checks pass. Preserve all original criteria; isolated review remains.

## Approach

Use a server-projected eligibility result or reproduce the exact bounded
duplicate/size rejection in the browser. Keep the POST boundary authoritative
and render an explicit unavailable reason before submission.

## Dependencies

AR-137 and ADR-0095 govern complete bounded host collections.

## Acceptance

- [ ] Duplicate and oversized host inventories cannot enable Route Lab.
- [ ] Browser eligibility and the authoritative POST handler agree on valid hosts.
- [ ] The UI renders an explicit bounded reason for ambiguous inventory.
- [ ] UI-to-POST contract and full dashboard suites pass.

## Implementation evidence

Commit `6a3bdaa` makes Route Lab derive eligibility from the complete bounded
host inventory and disables submission for duplicate or oversized evidence
with an explicit unavailable reason; the POST boundary remains authoritative.
Client/server contract regressions cover valid, duplicate, and oversized host
sets. The shared focused package passed 168 Python tests with 3 skips, four
post-review regressions, and 101 dashboard UI tests. Installed-browser and full
current-head evidence remain.
