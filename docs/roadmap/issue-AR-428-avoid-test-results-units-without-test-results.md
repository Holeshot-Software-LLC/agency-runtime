---
title: "AR-428: Avoid test-result analysis units when no results exist"
status: done
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

The active compact planner and its bounded repairer now share an explicit rule:
proposed, unexecuted tests require static review rather than invented test-result
analysis. Actual supplied results and permitted execution remain valid evidence
sources; mandatory execution gates and independent review are not waived.
Recipe 20 separates this planning context from older immutable receipts.

The original native packet and critic veto remain unchanged. Final recipe20 focused
164 / 1 skipped, production1151 / 3 skipped, UI224, routing, Ruff788 and frozen
conformance188/188 pass. Canonical artifact `ecf8a584` and all616 installed files
verify; Hermes refreshed on recipe20.

Fresh exact-request session `20260909_153129_1f3091` failed in81.860s with
`staffing_critic_rejected; critic_wrong_neighbor_selection`. Planner and recruiter
applied, but no routing decision/plan was retained and finalization is absent.
The response is not acceptance evidence. Observed diagnostic session
`20260909_153433_eef6b8` also failed wrong-neighbor staffing in78.821s. Its captured
actual critic packet contains four units, no test-evidence unit, and independent
static review of proposed code/tests. Type-design and silent-failure nominees
remain in the rejected team; the critic code does not identify a sole cause.
Owner configuration restored byte-for-byte, one packet captured, no observer errors.
Isolated criteria1/2 satisfied on the first pass; criterion3 returned no usable
result, then satisfied on the second default pass (`c8068ebd`). AR-428 is complete
for the unchanged planning criteria. Whole-host reliability and authoritative
completion remain unproven.

## Approach

Clarify the planner contract: static review of proposed tests is a review report; test-evidence requires supplied observed results or warranted execution. Preserve required independent correctness review and existing validation/critic gates. Validate the captured boundary before another native attempt.

## Dependencies

AR-404 owns the five-host reliability outcome. AR-423 and AR-426 retain their
native delivery and isolated acceptance gates.

## Acceptance

- [x] Exact native plan, selected contracts and critic rejection remain preserved.
- [x] Static test review and observed test evidence remain distinct without weakening independent assurance.
- [x] Focused and fast checks plus bounded native evidence verify the changed planning boundary.
