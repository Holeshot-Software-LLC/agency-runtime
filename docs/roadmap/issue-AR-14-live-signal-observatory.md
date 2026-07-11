---
title: "AR-14: Transform the dashboard into a live signal observatory"
status: done
category: roadmap
created: 2026-07-11
updated: 2026-07-11
tags: [dashboard, live-updates, visualization, accessibility, user-experience]
related:
  - docs/decisions/0029-secure-local-dashboard-and-bounded-observability.md
  - docs/decisions/0031-optional-user-dashboard-service-and-shared-configuration.md
  - docs/decisions/0032-adaptive-authenticated-dashboard-polling.md
supersedes: []
superseded_by: null
type: issue
epic: operations
issue_id: AR-14
priority: p1
tracker_url: null
depends_on: [AR-12, AR-13]
blocks: [AR-07]
---

# AR-14: Transform the dashboard into a live signal observatory

## Problem

The installed dashboard is secure and functional, but its overview is a static
administrative surface. Its LIVE label does not represent an update loop,
operators must refresh manually, recent bounded counts can look like totals,
and the presentation does not make routing, delegation, provider, and host
signals easy to understand at a glance.

## Current state

The package ships source-owned HTML, CSS, and JavaScript behind a loopback-only
authenticated server. The overview, activity, host, roster, snapshot, and
configuration endpoints are correct, but a full refresh rebuilds hidden views
and can overwrite an in-progress configuration form. There is no charting
layer, reduced-motion contract, live-update scheduler, or complete keyboard
model for tabs and confirmations.

## Approach

Create a Signal Observatory visual system with semantic source-owned controls,
honest metadata-derived charts, kinetic event transitions, and a responsive
layout. Keep the package dependency-free and offline: no CDN, browser token in
URLs, React runtime, or third-party chart payload.

Add one consolidated authenticated live endpoint and update it with recursive
single-flight polling. Pause in hidden tabs, resume immediately when visible,
back off transient failures, stop on terminal authentication errors, and apply
snapshots only when their stable revision changes. Keep host discovery, roster
governance, and configuration outside the fast loop so polling never performs
expensive native inspection or overwrites dirty settings.

## Dependencies

Depends on AR-12 for the authenticated packaged dashboard and AR-13 for the
cross-platform user service and shared configuration boundary. It blocks the
dashboard experience portion of AR-07 release readiness.

## Acceptance

- [x] The overview has product-specific responsive charts and a clear signal hierarchy derived only from real metadata.
- [x] Runtime activity updates automatically without a manual refresh and without overlapping requests.
- [x] Live polling pauses when hidden, resumes on visibility, backs off transient failures, and stops on terminal authentication failure.
- [x] Live refresh never inspects native hosts repeatedly or overwrites dirty configuration fields.
- [x] Charts provide readable summaries and never encode state by color alone.
- [x] Motion uses transform or opacity, is bounded, and is disabled by reduced-motion preferences.
- [x] Navigation, tabs, dialogs, controls, and responsive layouts are keyboard and touch accessible.
- [x] The dashboard remains self-contained, CSP-compatible, loopback-only, and free of external runtime dependencies.
- [x] Windows and Linux packaged-artifact checks include every new dashboard asset.

## Verification

- The complete Windows suite passed: 536 tests, with two expected
  platform-specific skips. The focused dashboard, store-index, and packaging
  suite passed 63 tests with one expected skip; the source-owned JavaScript
  suite passed 13 tests, including executable polling-race and lifecycle
  coverage.
- Desktop (1440 by 1000) and mobile (390 by 844) browser QA covered the live
  toggle, charts and summaries, Settings controls, accessible tab naming,
  responsive navigation, horizontal overflow, and console output. No browser
  warnings or errors were observed.
- The routing v1.1 evaluation passed every accuracy, determinism, concurrency,
  and performance gate.
- Rebuilt wheel and source artifacts passed strict Twine and distribution
  checks. The installed wheel served the authenticated dashboard and live
  endpoint in an isolated Windows environment; the same packaged assets and
  endpoint passed a direct-wheel WSL smoke under Python 3.12.3.
- Markdown metadata, documentation links, JavaScript syntax, Ruff, and Git
  whitespace checks passed. Tracker creation remains an outward-facing action
  pending explicit authorization.
