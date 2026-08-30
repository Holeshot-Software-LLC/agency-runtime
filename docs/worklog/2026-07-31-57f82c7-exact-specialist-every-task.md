---
title: "Worklog detail: Require an exact specialist for every task"
status: active
category: worklog
created: 2026-07-31
updated: 2026-07-31
tags: [workforce, inference, hiring, hooks, stewardship]
related:
  - docs/roadmap/issue-AR-204-reconcile-readme-story-contract.md
  - docs/roadmap/issue-AR-205-make-default-manager-inference-safe.md
  - docs/decisions/0122-use-one-agency-native-resident-steward.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: worklog
commit: 57f82c7
short: 57f82c7
date: 2026-07-31
pr: null
related_issues:
  - docs/roadmap/issue-AR-204-reconcile-readme-story-contract.md
  - docs/roadmap/issue-AR-205-make-default-manager-inference-safe.md
---

# Worklog detail: Require an exact specialist for every task

## Purpose

Make the README's specialist-workforce story true at the runtime boundary:
substantive work must have an inference-accepted specialist or newly hired
contractor, and the parent model may not silently answer as a generalist.

## Approach

Replace the imported universal manager pair with one parent-only
`agency-steward`, return both imported managers to the disableable roster, and
remove deterministic no-match selection. Recruiter inference now reasons from
an ideal role in an open-ended pool, may declare a gap without inventing a
roster candidate, and ordinary task hiring creates a distinct narrow role
instead of broadening a near-match. Codex and ZCode prompt submission blocks
when staffing is unavailable, and preflight rechecks the route after isolated
child-plan normalization so an unplanned identity cannot bypass that block.

## Challenges encountered

Compatibility tests had encoded the former resident-pair fallback as setup for
unrelated lifecycle assertions. Those fixtures were changed to use exact
control turns or complete content-free specialist bindings. This exposed and
then closed a genuine ordering defect: the first no-generalist check ran before
isolated-plan normalization could clear an unusable selection.

## Decisions and alternatives

[ADR-0122](../decisions/0122-use-one-agency-native-resident-steward.md)
governs the singleton steward and open-ended workforce. Deterministic nearest-
worker assignment, a universal generalist, and task-time amendment of a
near-match were rejected because each can produce plausible but unqualified
domain work without an inference-owned receipt.

## Verification

- Core routing/workforce suite: 166 passed.
- Preflight boundary: 30 passed.
- Native host hooks: 94 passed.
- Adapter parity: 48 passed.
- Header/store: 27 passed.
- MCP, ZCode, and Claude: 64 passed, 5 intentional skips.
- Dashboard client: 110 passed.
- Ruff check passed for `agency_runtime`, `tests`, and `scripts`; all 602 Python
  files were format-current; Markdown metadata checked 569 documents.
- Four new decision-mutation anchors and their named baseline tests passed.

## Follow-ups

Run the complete decision-conformance evaluator and named fast spine, update
the recovery evidence, merge and install the exact build, then run one
trust-bypassed Codex product trial with zero response corrections under
[AR-204](../roadmap/issue-AR-204-reconcile-readme-story-contract.md).
