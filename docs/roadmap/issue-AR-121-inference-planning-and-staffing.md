---
title: "AR-121: Implement inference-first planning and deterministic staffing"
status: open
category: roadmap
created: 2026-07-21
updated: 2026-07-21
tags: [planning, recruitment, selection, inference]
related:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/decisions/0080-plan-before-recruiting-from-the-whole-workforce.md
supersedes: []
superseded_by: null
type: issue
epic: routing
issue_id: AR-121
priority: p0
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/134
depends_on: [AR-120]
blocks: [AR-122, AR-124, AR-125]
---

# AR-121: Implement inference-first planning and deterministic staffing

## Problem

Routing does not yet plan production-complete typed work before considering
agents or recruit from the complete compact workforce with deterministic
coverage, composition, and disabled-shadow enforcement.

## Current state

Inference and deterministic routes select bounded specialists, but the current
pipeline conflates retrieval, planning, selection, and assurance signals.

## Approach

Add bounded planner and recruiter schemas, whole-index nomination with detailed
card retrieval, deterministic staffing verification, three-layer ranking,
strict and fast modes, readable abstention, and exact provider receipts.

## Dependencies

AR-120 supplies the normalized, versioned workforce index.

## Acceptance

- [ ] Configured inference plans before recruiting and sees the whole workforce.
- [ ] Deterministic code enforces coverage, eligibility, composition, and budgets.
- [ ] Disabled and unavailable semantic winners are visible but never activated.
- [ ] Degraded deterministic fallback abstains on unsafe or weak coverage.
