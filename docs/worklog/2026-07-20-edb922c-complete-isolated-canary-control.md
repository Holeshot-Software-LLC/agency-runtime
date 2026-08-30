---
title: "Complete isolated canary control"
status: active
category: worklog
created: 2026-07-20
updated: 2026-07-20
tags: [roadmap, canary, runtime-control, evidence]
related:
  - docs/roadmap/issue-AR-111-honor-global-mode-in-isolated-canaries.md
  - docs/decisions/0076-bind-isolated-canaries-to-explicit-agency-modes.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: worklog
commit: edb922c9f74ea6140432630927704e76c895a041
short: edb922c
date: 2026-07-20
pr: https://github.com/Holeshot-Software-LLC/agency-runtime/pull/114
related_issues:
  - docs/roadmap/issue-AR-111-honor-global-mode-in-isolated-canaries.md
---

# Worklog detail: Complete isolated canary control

## Purpose

Convert AR-111 from an in-progress defect record into an evidence-backed done
record after exact installed A/B proof and the complete hosted matrix passed.

## Approach

Preserve the original failed native-only observation, then record the exact
post-fix managed bundle, Agency-on trace, native-only zero-evidence result,
global control generations, guaranteed restoration, and cross-platform gates.

## Challenges encountered

The first local edit used `complete`, but issue documents use the validated
`done` enum. The unpushed commit was corrected before it entered the durable
worklog or remote branch.

## Decisions and alternatives

The issue was not closed from focused tests alone. Completion required a real
Codex A/B run, exact 100% hosted coverage, performance/UI gates, and every
Windows/Linux full-suite job.

## Verification

- Exact installed Agency-on and native-only Codex canaries passed.
- Hosted Windows/Linux artifact, analysis, portability, full-suite, coverage,
  performance, and dashboard UI checks passed.
- Documentation validation accepts the `done` status and synchronized registry.

## Follow-ups

Merge PR #114, close tracker #115, and re-run strict tracker parity.
