---
title: "Live Signal Observatory"
status: active
category: worklog
created: 2026-07-11
updated: 2026-07-11
tags: [worklog, dashboard, visualization, live-updates, accessibility]
related:
  - docs/roadmap/issue-AR-14-live-signal-observatory.md
  - docs/decisions/0029-secure-local-dashboard-and-bounded-observability.md
  - docs/decisions/0031-optional-user-dashboard-service-and-shared-configuration.md
  - docs/decisions/0032-adaptive-authenticated-dashboard-polling.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: worklog
commit: "63ea805be52d7bb014b8416c6a7fb600305759db"
short: "63ea805"
date: 2026-07-11
pr: null
related_issues:
  - docs/roadmap/issue-AR-14-live-signal-observatory.md
---

# Worklog detail: Turn dashboard into a live signal observatory

## Purpose

Transform the secure installed dashboard from a static administrative surface
into a polished, responsive operations experience that shows real runtime
movement without weakening its loopback, authentication, privacy, or
cross-platform packaging boundaries.

## Approach

Rebuilt the overview as a Signal Observatory with a product-specific visual
system, bounded routing and delegation charts, live event transitions, host
posture, and provider evidence. Controls and SVG charts remain semantic,
source-owned package assets, so the wheel stays offline and dependency-light
while providing the interaction quality associated with shadcn-style controls
and Ant/G2-style visualizations.

Added one authenticated metadata-only live endpoint. It reads bounded activity
once, derives honest observed-window summaries, returns a stable content
revision, and excludes optionally captured details. Recursive single-flight
polling pauses while hidden, resumes after visibility and BFCache restoration,
uses capped retry backoff, and stops on authentication failure. A slower
control-plane tier keeps hosts, roster, snapshots, and configuration out of the
fast path.

Full and live refreshes use abort controllers and generation identities.
Mutations cancel older reads, successful operations are separated from
best-effort reconciliation, and dirty Settings fields are never replaced by a
background snapshot. Global recent-read indexes keep every live query on a
matching SQLite index without a temporary sort.

## Challenges encountered

- A packaged Python dashboard has no frontend build pipeline and must work
  offline on Windows and Linux. Pulling in React, shadcn, or Ant Charts would
  have added a second runtime and supply chain, so their interaction and chart
  quality was implemented as small audited primitives.
- Adversarial review found startup, mutation, BFCache, and full-refresh races.
  Controller and generation checks now reject every stale completion.
- The first test pass asserted polling markers statically but did not execute
  the lifecycle. A dependency-free Node VM harness now runs the real
  `app.js` against deterministic DOM, fetch, abort, and timer doubles.
- The Windows sandbox could not host build-backend subprocesses, and WSL lacked
  `ensurepip`. Artifact verification therefore used an approved isolated
  Windows environment and an offline WSL direct-wheel runtime smoke without
  changing the Linux system.

## Decisions and alternatives

[ADR-0032](../decisions/0032-adaptive-authenticated-dashboard-polling.md)
records the adaptive bearer-authenticated polling and source-owned
visualization choice. EventSource was rejected because it cannot carry the
bearer header, streaming connections would still poll SQLite, whole-dashboard
interval refreshes would repeat expensive work, and CDN or framework assets
would violate the self-contained offline contract.

## Verification

- Full Windows suite: 536 passed, 2 expected platform-specific skips.
- Focused dashboard, store-index, and packaging suite: 63 passed, 1 expected
  skip. The JavaScript chart and executable lifecycle suite passed 13 tests.
- Desktop 1440 by 1000 and mobile 390 by 844 browser QA covered live controls,
  charts, Settings, responsive navigation, overflow, accessible tab naming,
  and console output; no warnings or errors were observed.
- Routing v1.1 passed every accuracy, determinism, concurrency, and performance
  gate.
- Rebuilt wheel and source artifacts passed strict Twine and content checks.
  The installed wheel served the authenticated dashboard and live endpoint in
  an isolated Windows environment and through WSL Python 3.12.3.
- Ruff, JavaScript syntax, compileall, high-severity Bandit, Markdown metadata,
  repository-link validation, and Git whitespace checks passed.

## Follow-ups

- Create the same-repository `[AR-14]` tracker issue and write its URL back
  only after explicit authorization for that outward-facing action.
- Hosted Linux CI and live host canaries remain part of
  [AR-07](../roadmap/issue-AR-07-public-release-readiness.md); deterministic
  artifact evidence is not presented as a live production canary.
