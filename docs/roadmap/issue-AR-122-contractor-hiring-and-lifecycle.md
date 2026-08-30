---
title: "AR-122: Implement governed contractor hiring and workforce lifecycle"
status: done
category: roadmap
created: 2026-07-21
updated: 2026-08-12
tags: [contractors, hiring, lifecycle, governance]
related:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-264-compile-actionable-contractor-execution-profiles.md
  - docs/decisions/0081-compile-contractors-from-governed-structured-contracts.md
supersedes: []
superseded_by: null
type: issue
epic: roster-governance
issue_id: AR-122
priority: p0
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/135
depends_on: [AR-120, AR-121]
blocks: [AR-123, AR-125, AR-264]
---

# AR-122: Implement governed contractor hiring and workforce lifecycle

## Problem

Agency cannot yet prove a capability gap, choose amend versus hire, compile a
safe contractor, use it immediately, or preserve its employment lifecycle and
performance history.

## Current state

Roster ingestion and versioned activation are governed, but no inference-only
employment workflow or contractor-specific identity and evidence exists.

## Approach

Add gap and duplicate evidence, fixed-template contract compilation, independent
hiring criticism, limits and high-risk approval, stable identities, known
contractors, promotion, amendment, merge, suspension, disabling, and retirement.

## Dependencies

AR-120 provides comparison contracts and AR-121 supplies typed uncovered work.

## Acceptance

- [x] A proven real gap hires, enables, activates, and reports a contractor.
- [x] Duplicate gaps amend a coherent worker; unsafe merges are rejected.
- [x] Known contractors are audited, enabled, visible, and exercised.
- [x] Promotion removes only the display moniker and preserves identity/history.
