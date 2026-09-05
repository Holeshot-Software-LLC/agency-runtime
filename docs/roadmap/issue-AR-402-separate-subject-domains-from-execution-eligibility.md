---
title: "AR-402: Separate subject domains from execution eligibility"
status: in_progress
category: roadmap
created: 2026-09-05
updated: 2026-09-05
tags: [workforce, staffing, reliability]
related:
  - docs/decisions/0217-keep-subject-domains-out-of-execution-authority.md
  - docs/roadmap/issue-AR-394-recruiter-teams-fail-or-mis-select.md
  - docs/roadmap/issue-AR-400-preserve-staffing-progress-across-empty-gaps.md
supersedes: []
superseded_by: null
type: issue
epic: reliability
issue_id: AR-402
priority: p1
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/667
depends_on: []
blocks: []
---

# AR-402: Separate subject domains from execution eligibility

## Problem

Category-derived domain tags became mandatory eligibility and team-coverage predicates. A valid backend implementation unit was constrained to Roblox's worker while the API and backend planners correctly lacked modification authority. Retrieval alone cannot repair that contract mismatch.

## Current state

The independent 2026-09-05 review reproduced the defect at main `e6531004`.
The owner requested implementation, PR merge, installation and smoke testing of
all harnesses. Package phase: implementing. No live outcome is claimed yet.

## Approach

Use domain labels as descriptive recall and inference evidence, not execution authority or mandatory team coverage. Preserve explicit authority, capability, tool, platform, stack and out-of-scope constraints. Test representative work against the shipped audited roster rather than fabricated specialist identities.

## Dependencies

Delivered with AR-400, AR-401 and AR-402 as one bounded staffing-correctness package.
Existing native host trust and gateway credentials remain operator-owned.

## Acceptance

- [ ] Subject domain mismatch alone neither rejects a candidate nor forces extra team members; domains remain visible to recall and the recruiter.
- [ ] Audited planning-only specialists remain ineligible for implementation, and explicit safety constraints continue to reject invalid teams.
- [ ] Representative backend, frontend, operations and review units have a faithful executable candidate or an inference-declared gap against the packaged roster, without a test-only authority upgrade.
