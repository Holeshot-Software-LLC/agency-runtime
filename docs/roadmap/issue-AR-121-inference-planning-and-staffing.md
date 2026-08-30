---
title: "AR-121: Implement inference-first planning and deterministic staffing"
status: done
category: roadmap
created: 2026-07-21
updated: 2026-08-12
tags: [planning, recruitment, selection, inference]
related:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/decisions/0080-plan-before-recruiting-from-the-whole-workforce.md
  - docs/decisions/0103-bind-named-regulated-assurance-to-typed-staffing.md
  - docs/roadmap/issue-AR-179-fail-named-regulated-assurance-gaps-closed.md
supersedes: []
superseded_by: null
type: issue
epic: routing
issue_id: AR-121
priority: p0
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/134
depends_on: [AR-120]
blocks: [AR-122, AR-124, AR-125, AR-179]
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

- [x] Configured inference plans before recruiting and sees the whole workforce.
- [x] Deterministic code enforces coverage, eligibility, composition, and budgets.
- [x] Disabled and unavailable semantic winners are visible but never activated.
- [x] Degraded deterministic fallback abstains on unsafe or weak coverage.

These boxes record the historical AR-121 contract mapped in
`AR-119-acceptance-evidence.md`. ADR-0118 and AR-255 now govern the stricter
inference-only selection contract; this issue is not authority for a
deterministic production selector.
