---
title: "AR-123: Add complete workforce CLI and live dashboard operations"
status: open
category: roadmap
created: 2026-07-21
updated: 2026-07-21
tags: [cli, dashboard, workforce, operations]
related:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/decisions/0081-compile-contractors-from-governed-structured-contracts.md
supersedes: []
superseded_by: null
type: issue
epic: dashboard
issue_id: AR-123
priority: p0
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/136
depends_on: [AR-122]
blocks: [AR-125]
---

# AR-123: Add complete workforce CLI and live dashboard operations

## Problem

Operators need complete, safe, discoverable workforce and hiring controls in
both automation-friendly CLI output and the live dashboard.

## Current state

Existing roster controls support enable and disable plus evidence browsing, but
not planning, hiring, promotion, amendment, consolidation, or full lifecycle.

## Approach

Add human and JSON CLI commands and an accessible Workforce and Hiring dashboard
with live events, staffing graphs, model evidence, comparisons, performance,
promotion readiness, and confirmed lifecycle mutations.

## Dependencies

AR-122 defines the authoritative workforce operations and evidence.

## Acceptance

- [ ] Every lifecycle operation is available in CLI and dashboard.
- [ ] Protected resident managers cannot be disabled.
- [ ] Destructive actions require explicit confirmation and current generations.
- [ ] Live UI remains responsive, accessible, reduced-motion safe, and fully tested.
