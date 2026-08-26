---
title: "AR-305: Normalize planner novelty absence sentinels"
status: in_progress
category: roadmap
created: 2026-08-26
updated: 2026-08-26
tags: [workforce, inference, planning, validation]
related:
  - CHANGELOG.md
  - docs/roadmap/issue-AR-297-complete-unattended-container-bootstrap.md
  - docs/roadmap/handoffs/issue-AR-297.md
  - agency_runtime/core/workforce/intent.py
  - tests/test_workforce_intent.py
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: workforce
issue_id: AR-305
priority: p0
tracker_url: null
depends_on: []
blocks: [AR-297]
---

# AR-305: Normalize planner novelty absence sentinels

## Problem

The compact planner schema represents an absent `novel_capability` as an empty
string. A live local Qwen response instead returned the schema-valid string
`"false"`. Compilation interpreted it as a genuine new capability, making an
otherwise covered accessibility unit require impossible `capability:false`
and forcing strict staffing to abstain.

## Current state

- A private planner-only diagnostic reproduced the exact 397-byte AR-297
  request and compiled `"false"` into `capability:false`.
- The Accessibility Auditor and Section 508 specialist covered every legitimate
  requirement; the false capability was the only uncovered axis.
- The candidate normalizes only conventional stringified absence values
  `false`, `none`, and `null` to no novelty at both capability compilation and
  unknown-domain admission boundaries.
- Focused planning, inference, and selection coverage passes 158 tests with one
  expected skip; changed-file Ruff, formatting, and diff checks pass.
- Tracker creation is prohibited by the active task.

## Approach

Canonicalize bounded stringified absence before capability normalization and
reuse the same canonical value when deciding whether a genuinely novel domain
may enter the plan. Preserve all other normalized identifiers as real gap
claims and retain the existing rejection when a claimed novelty already exists
in the workforce ontology.

## Dependencies

- The compact intent schema remains string-based for provider compatibility.
- Inference retains sole staffing authority; this boundary repair only removes
  a false requirement and does not select a worker.
- Tracker creation requires separate outward-write authorization.

## Acceptance

- [x] `false`, `none`, and `null` cannot become required capabilities.
- [x] Those sentinels cannot authorize an otherwise unknown domain.
- [x] Genuine novel capability identifiers and existing-ontology rejection are
      unchanged.
- [x] Focused warning-strict tests and changed-file static checks pass.
- [ ] A live strict/additive preflight selects and loads the correct audited
      specialist with complete prompt visibility.
- [ ] A same-repository tracker is created and linked after explicit
      authorization.
