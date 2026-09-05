---
title: "AR-400: Preserve staffing progress across empty gaps"
status: in_progress
category: roadmap
created: 2026-09-05
updated: 2026-09-05
tags: [workforce, staffing, reliability]
related:
  - docs/roadmap/issue-AR-383-inferred-subject-context-fails-its-own-projection.md
  - docs/roadmap/issue-AR-401-enforce-preflight-deadlines-at-provider-boundaries.md
  - docs/roadmap/issue-AR-402-separate-subject-domains-from-execution-eligibility.md
supersedes: []
superseded_by: null
type: issue
epic: reliability
issue_id: AR-400
priority: p1
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/665
depends_on: []
blocks: []
---

# AR-400: Preserve staffing progress across empty gaps

## Problem

Valid recruiter gap rows may have empty rankings. Restaffing discarded each successful hire while another empty gap remained, including atomic preflight's deferred-hire path.

## Current state

The independent 2026-09-05 review reproduced the defect at main `e6531004`.
The owner requested implementation, PR merge, installation and smoke testing of
all harnesses. Package phase: demo_ready. Focused regressions and the named fast
spine pass (1004 passed, three skipped); 182 curated conformance mutations are
killed. Implementation checkpoints are `47ab9fce`, `e9d8ecea` and `af366dd8`.
Installed/live host outcomes remain due; AR-403 separately records live recall timing.

## Approach

Retain each resolved unit, preserve other declared gaps and assignments to amended workers, and re-run the existing verifier against the current snapshot. Do not commit pending workers before preflight readiness.

## Dependencies

Delivered with AR-400, AR-401 and AR-402 as one bounded staffing-correctness package.
Existing native host trust and gateway credentials remain operator-owned.

## Acceptance

- [ ] One and two empty gaps retain every completed assignment with direct and deferred commits; a per-turn cap preserves the first assignment and names the remaining gap.
- [ ] Amending a worker already nominated on another unit preserves that nomination and revalidates the full proposal.
- [ ] The bounded package reaches main through a PR, is installed, and records deterministic smoke and a live attempt or explicit operator/platform blocker for each of the five harnesses.
