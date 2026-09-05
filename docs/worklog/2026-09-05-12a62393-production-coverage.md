---
title: "Worklog: measure all production dashboard modules"
status: active
category: worklog
created: 2026-09-05
updated: 2026-09-05
tags: [dashboard, testing, coverage]
related:
  - docs/worklog/README.md
  - docs/roadmap/issue-AR-406-restore-dashboard-function-coverage.md
  - docs/roadmap/issue-AR-152-bound-dashboard-live-listeners.md
  - docs/decisions/0220-measure-dashboard-coverage-over-production-modules.md
supersedes: []
superseded_by: null
type: worklog
commit: 12a62393613452fb322697b4cde48d8c74949422
short: 12a62393
date: 2026-09-05
pr: https://github.com/Holeshot-Software-LLC/agency-runtime/pull/684
related_issues:
  - docs/roadmap/issue-AR-406-restore-dashboard-function-coverage.md
  - docs/roadmap/issue-AR-152-bound-dashboard-live-listeners.md
---

# Worklog: measure all production dashboard modules

## Purpose

Check the relevance of the newly filed coverage gap instead of assuming its
initial proposal was correct. The failing 91.12 percent aggregate included test
fixture functions. All seven shipped product modules already passed unchanged
95/86/93 floors. AR-152's old listener defect was already repaired.

## Approach

Add one identical recursive production inclusion argument to local and hosted
Node coverage commands. Pin their entire argument vectors in two regressions,
retaining all production modules, UI tests, and numeric floors. Add current
listener/teardown evidence without changing working UI code.

## Challenges encountered

The initial AR-406 callback/exclusion assumptions were incorrect. Preserve
them in its historical section and replace them explicitly through ADR-0220
before isolated verification. Raw V8 output has 704 test-function entries,
86 unexecuted; exercising unused fixture callbacks would not prove more product
behavior. Both new command-contract cases failed before the scope correction.

## Decisions and alternatives

ADR-0220 defines product coverage independently of fixture implementation.
Do not lower a floor, omit a production module, change a skip, or claim a coverage
increase: the denominator changed. Future nested .js modules are included;
a new script extension would require an explicit contract update.

## Verification

- Actual configured local UI gate: 138 passed, zero failures/skips; all seven
  product modules, 96.92 percent lines, 86.62 branches, 95.71 functions.
- Both regression cases red first; all 163 workflow-contract tests pass after.
- Fresh named spine: 1030 passed, three existing skips in 64.98s.
- Ruff and format pass; strict documentation and metadata checks pass.
- Protected conformance inputs are unchanged from the preceding baseline and
  182/182 mutation kill run. No new native browser, Windows, artifact or host
  canary is inferred. No exhaustive workflow was dispatched.

## Follow-ups

Freeze AR-406/152 acceptance to this candidate and obtain isolated verdicts.
Only then complete the records, merge PR #684 and close tracker #682. Other
backlog and attended native-host gates remain separate outcomes.
