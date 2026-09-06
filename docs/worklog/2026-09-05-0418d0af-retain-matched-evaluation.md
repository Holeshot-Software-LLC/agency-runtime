---
title: "Retain AR-125 matched evaluation and live-proof obligations"
status: active
category: worklog
created: 2026-09-05
updated: 2026-09-05
tags: [backlog, evaluation, evidence]
related:
  - docs/roadmap/issue-AR-125-workforce-and-one-shot-evaluation.md
  - docs/roadmap/AR-404-oldest-first-reconciliation-20260905.md
  - docs/decisions/0102-defer-one-shot-application-evaluation.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: worklog
commit: 0418d0afbd0cdd145346bca597f7595cb65dc788
short: 0418d0af
date: 2026-09-05
pr: null
related_issues:
  - docs/roadmap/issue-AR-125-workforce-and-one-shot-evaluation.md
---

# Worklog: retain matched evaluation obligations

## Purpose

Give the fourth oldest unfinished record a current disposition without treating
a passing evaluator as the evidence it must eventually collect.

## Approach

Retain AR-125 open and all six acceptance states unchanged. Label the checked
Windows/Linux result as historical candidate 29da6eca, distinguish current
fixture tests and installed contract smoke from live proof, and record a
bounded sequence for the configured/held-out study, matched outcomes and host
artifacts. Add a recovery capsule and advance AR-404's review queue to AR-127.

## Challenges encountered

No new failure. The current session remains unverified; older live-success
notes cannot contradict that limitation or supply fresh matched evidence.

## Decisions and alternatives

Apply existing ADR-0102: complete one-shot applications stay in deferred AR-178.
Retiring that expensive corpus from the gate does not retire the relevant
selection/value requirements. No new product decision or acceptance waiver.

## Verification

33 local worker-comparison, workforce-selection, upstream-selection and
full-roster regressions pass in 2.68s. These include identical-binding and
malformed-arm validity checks, not provider-backed studies. Strict docs/metadata
pass for 1119 files before this detail; policy availability, worklog, strict
tracker parity and diff checks pass. Runtime/test/script/workflow and AR-119
matrix/vision diffs against bc392228 are empty. This turn's fast spine/UI results
remain reusable source evidence. No hosted dispatch, live draw or Windows run.

## Follow-ups

Merge this record reconciliation, retain #138 open, then inspect AR-127.
AR-125 remains the owner of the still-unproven matched study and live evidence.
