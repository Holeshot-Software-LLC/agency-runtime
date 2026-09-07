---
title: "File required staffing call reservations (AR-409)"
status: active
category: worklog
created: 2026-09-07
updated: 2026-09-07
tags: [workforce, budgets, reliability]
related:
  - docs/roadmap/issue-AR-409-reserve-required-staffing-calls.md
  - docs/decisions/0235-reserve-required-staffing-calls-before-optional-work.md
supersedes: []
superseded_by: null
type: worklog
commit: 96a048d682721da5ce5cbc92e8f5ce18f113ff10
short: 96a048d6
date: 2026-09-07
pr: null
related_issues: [docs/roadmap/issue-AR-409-reserve-required-staffing-calls.md]
---

# Worklog detail: File required staffing call reservations (AR-409)

## Purpose

Create tracker #735, canonical AR-409 and ADR-0235 with reciprocal registry and
dependency records before publishing the separately reviewed implementation.

## Approach

Reserve mandatory downstream calls within unchanged owner limits and allow at
most one actual optional subject request. ADR-0235 supplements ADR-0132 and
ADR-0197; AR-408 remains the prerequisite truthful-receipt correction.

## Challenges encountered

Parallel tracker creation temporarily preceded local main's matching filing.
This docs-only pair can be carried into that publication without prematurely
claiming the runtime or installed evidence is complete.

## Decisions and alternatives

Do not raise explicit caps, skip the strict critic or promise equal model
outcomes. Subject plus both repairs and a critic needs six calls rather than
five. See ADR-0235 for the conservative cache/gap reservation tradeoff.

## Verification

The first documentation check found only tracker URLs still null in two local
uncommitted evidence/capsule drafts; those drafts are outside this filing and
were updated before the checkpoint validation. `git diff --check` passed.
Implementation tests and acceptance evidence are intentionally a later slice.

## Follow-ups

AR-409 retains AR-408 integration, source-bound acceptance, installed live
verification and PR/merge. No acceptance verdict or installed claim is made.

Merge `c095616a` brings only the parallel filing/ADR checkpoint into AR185 publication so remote735 and canonical records stay in parity. Runtime implementation remains on its own branch.
