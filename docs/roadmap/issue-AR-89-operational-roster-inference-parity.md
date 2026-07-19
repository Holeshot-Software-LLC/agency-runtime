---
title: "AR-89: Expose roster governance and inference health operationally"
status: in_progress
category: roadmap
created: 2026-07-18
updated: 2026-07-19
tags: [dashboard, cli, roster, inference, observability]
related:
  - docs/roadmap/issue-AR-12-installed-operations-dashboard.md
  - docs/roadmap/issue-AR-28-reversible-agent-activation-controls.md
  - docs/roadmap/issue-AR-86-govern-complete-upstream-roster-lifecycle.md
  - docs/roadmap/issue-AR-87-bounded-native-delegation-plans.md
  - docs/decisions/0029-secure-local-dashboard-and-bounded-observability.md
  - docs/decisions/0032-adaptive-authenticated-dashboard-polling.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: operations
issue_id: AR-89
priority: p1
tracker_url: "https://github.com/Holeshot-Software-LLC/agency-runtime/issues/90"
depends_on: [AR-12, AR-28, AR-80, AR-86, AR-87]
blocks: []
---

# AR-89: Expose roster governance and inference health operationally

## Problem

Basic roster state and agent toggles do not let operators inspect the complete
routing contract, audit queue, active/candidate history, upstream delta status,
or authoritative inference degradation required by the architecture.

## Current state

The authenticated dashboard and shared configuration writer already expose
runtime control, agent activation, recent evidence, route testing, full
governance projections, provider failure history, rich roster filters, and
bounded remediation history. CLI route and explain diagnostics now bind the
single exact verified enabled installation when one exists, so the selected
specialists and visible candidate ranking share the same truthful host
eligibility context. CLI status and the authenticated dashboard now consume one
bounded, secret-safe inference-health projection. Route Lab presents the
complete recommendation-only unit-to-specialist plan, including assignment
strength, native mechanism, and the evidence required to distinguish a plan
from execution. The installed Windows service, browser, accessibility,
performance, and exact coverage gates pass; Linux hosted service proof remains.

## Approach

Build shared typed services consumed by CLI and dashboard for source revisions,
hashes, audits, findings, active/candidate comparison, conflict and requirement
metadata, activation history, upstream status, provider-chain health,
inference-required/degraded state, parent/child routing, delegation plans and
outcomes, and requested/router/actual-model reconciliation. Keep responses
bounded, redacted, authenticated, accessible, animated, and live-updating.

## Dependencies

AR-86 owns governance data, AR-87 owns delegation plans, AR-80 owns optional
provider degradation, and the existing dashboard and activation records own the
secure operational boundary.

## Acceptance

- [x] CLI and dashboard expose equivalent governance and inference-health information.
- [x] Roster search filters division, capability, authority, host, platform, and tool.
- [x] Audit queue, findings, candidate comparison, conflicts, requirements, and history are visible.
- [x] Provider failures and mandatory-inference degradation are authoritative and live-updating.
- [x] Parent/child routing, delegation plans, outcomes, and model reconciliation are visible.
- [ ] The optional service remains durable and secure on Windows and Linux.
- [x] Accessibility, performance, Node coverage, Python coverage, and installed-service gates pass.
