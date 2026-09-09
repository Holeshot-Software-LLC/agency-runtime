---
title: "AR-428: Avoid test-result analysis units when no results exist"
status: open
category: roadmap
created: 2026-09-09
updated: 2026-09-09
tags: [reliability, workforce, evidence]
related:
  - docs/decisions/0200-bind-the-strict-critic-to-the-advisory-doctrine.md
  - docs/roadmap/issue-AR-404-evidence-led-backlog-completion.md
  - docs/worklog/2026-09-09-hermes-context-spill.md
supersedes: []
superseded_by: null
type: issue
epic: reliability
issue_id: AR-428
priority: p1
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/826
depends_on: []
blocks: []
---

# AR-428: Avoid test-result analysis units when no results exist

## Problem

A fresh Hermes supplied-code-only request explicitly forbids execution. The planner invents a test-evidence unit that interprets unexecuted tests. The recruiter selects a role whose contract expects supplied completed test results, and the independent critic vetoes the team. The captured packet supports preserving the veto, not bypassing it.

## Current state

Exact retained evidence has been inspected. No validator or critic verdict has
been overridden. Source repair and acceptance remain pending.

## Approach

Clarify the planner contract: static review of proposed tests is a review report; test-evidence requires supplied observed results or warranted execution. Preserve required independent correctness review and existing validation/critic gates. Validate the captured boundary before another native attempt.

## Dependencies

AR-404 owns the five-host reliability outcome. AR-423 and AR-426 retain their
native delivery and isolated acceptance gates.

## Acceptance

- [ ] Exact native plan, selected contracts and critic rejection remain preserved.
- [ ] Static test review and observed test evidence remain distinct without weakening independent assurance.
- [ ] Focused and fast checks plus bounded native evidence verify the changed planning boundary.
