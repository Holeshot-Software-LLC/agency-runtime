---
title: "AR-119: Implement inference-first real-time workforce and contractor lifecycle"
status: in_progress
category: roadmap
created: 2026-07-21
updated: 2026-07-21
tags: [routing, workforce, contractors, delegation, evaluation]
related:
  - docs/decisions/0080-plan-before-recruiting-from-the-whole-workforce.md
  - docs/decisions/0081-compile-contractors-from-governed-structured-contracts.md
  - docs/decisions/0082-schedule-assurance-by-artifact-lifecycle.md
supersedes: []
superseded_by: null
type: issue
epic: routing
issue_id: AR-119
priority: p0
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/132
depends_on: [AR-115, AR-116, AR-118]
blocks: []
---

# AR-119: Implement inference-first real-time workforce and contractor lifecycle

## Problem

Agency can route audited specialists, but it does not yet operate as the
inference-first, real-time company required to produce production-complete
applications while keeping the parent agent small. Recruitment metadata,
typed planning, contractor hiring, lifecycle assurance, operator controls, and
application-level evidence are not yet one coherent system.

## Current state

The audited roster, turn-scoped activation, resident managers, native-child
receipts, provider evidence, CLI, and dashboard provide a strong base. The
complete contract and completion gates are authoritative in tracker issue
[#132](https://github.com/Holeshot-Software-LLC/agency-runtime/issues/132).
AR-120 through AR-125 divide implementation into independently verifiable
slices without narrowing that umbrella contract.

## Approach

Plan typed work before naming agents; recruit from a normalized projection of
the entire workforce; verify staffing deterministically; hire only proven gaps
through governed structured contracts; preserve host-owned delegation; schedule
assurance from artifact lifecycle; expose workforce operations in CLI and the
dashboard; and grade installed application outcomes rather than agent activity.

## Dependencies

AR-115 establishes trustworthy live selection, AR-116 bounds native-child
routing and provider choice, and AR-118 reconciles activation evidence.

## Acceptance

- [ ] AR-120 through AR-125 are complete and tracker-evidenced.
- [ ] Every completion gate in tracker issue #132 has direct current evidence.
- [ ] The final hosted matrix, installed artifacts, four host contracts, and live canaries pass.
- [ ] The merged and reinstalled artifact is verified before this item closes.
