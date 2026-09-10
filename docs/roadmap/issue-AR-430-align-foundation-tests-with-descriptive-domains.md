---
title: "AR-430: Align staffing-foundation tests with descriptive subject domains"
status: open
category: roadmap
created: 2026-09-09
updated: 2026-09-09
tags: [tests, workforce, reliability]
related:
  - docs/decisions/0217-keep-subject-domains-out-of-execution-authority.md
  - docs/roadmap/issue-AR-402-separate-subject-domains-from-execution-eligibility.md
  - docs/worklog/2026-09-09-hermes-nomination-relevance.md
supersedes: []
superseded_by: null
type: issue
epic: reliability
issue_id: AR-430
priority: p2
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/835
depends_on: []
blocks: []
---

# AR-430: Align staffing-foundation tests with descriptive subject domains

## Problem

Two optional staffing-foundation assertions expect domain-only coverage to add
or prefer a worker. AR-402 / ADR-0217 make subject domains descriptive, not
mandatory execution or team coverage. These assertions fail on unchanged main.

## Current state

Deferred outside AR-429's bounded Hermes nomination repair. Baseline main
`6d76e6a7d1eb0e02f6c3fd57a812d9ff88db63d7` reproduces both failures in0.11s;
the AR-429 focused run has the same2 failures,240 passes and1 skip. Exact logs
are `AR-429-baseline-foundation-20260909.txt` and `AR-429-focused-20260909.txt`.
Affected tests are `test_subject_matter_reviewer_can_complement_test_evidence_owner`
and `test_margin_compares_complete_alternative_teams_not_partial_near_neighbors`
in `tests/test_workforce_staffing_foundation.py`. No fixture changes yet.

## Approach

Review and update the fixtures around actual authority/capability/stack coverage
where team complements are intended, and assert domain-only differences do not
force staffing. Do not restore domain-driven selection to satisfy stale tests.

## Dependencies

ADR-0217 governs semantics. AR-429 records discovery but does not implement this
maintenance. The named fast production spine remains a separate required gate.

## Acceptance

- [ ] The two unchanged-main failures and their relation to ADR-0217 remain documented.
- [ ] Meaningful fixtures cover typed complements and alternative-team margins without treating subject labels as mandatory coverage.
- [ ] Focused foundation tests and required fast checks pass without changing inference ownership or domain semantics.
