---
title: "Apply refresh ownership checks to late failures"
status: active
category: worklog
created: 2026-09-07
updated: 2026-09-07
tags: [dashboard, concurrency, acceptance]
related:
  - docs/roadmap/issue-AR-138-coherent-observable-dashboard-ui.md
  - docs/roadmap/acceptance/evidence/AR-138-repaired-dashboard-20260907.md
  - docs/decisions/0032-adaptive-authenticated-dashboard-polling.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: worklog
commit: cd35aa2c09a5498404f13a41e0df6561e103655d
short: cd35aa2c
date: 2026-09-07
pr: https://github.com/Holeshot-Software-LLC/agency-runtime/pull/700
related_issues:
  - docs/roadmap/issue-AR-138-coherent-observable-dashboard-ui.md
---

# Worklog detail: Ignore obsolete refresh failures

## Purpose

Independent acceptance contradicted AR-138 criterion 1: an older full refresh
could publish a late error after a newer request had already succeeded.
Preserve that complete first review at 25b9a67a and fix the actual race.

## Approach

Apply the success path's ownership/generation rule to errors as well. Ignore
obsolete full-refresh failures before changing connection, stale or auth state.
Use the same rule for control request/commit generations and live snapshot
errors before they reach live retry or reconciliation handlers. Preserve false
cancellation results through both reconciliation wrappers.

Current network, HTTP and expired-token failures still surface. No retry,
provider, credential or authentication policy changes. ADR-0032 still governs
single-flight polling and obsolete-generation rejection.

## Challenges encountered

Twenty-four initial late-failure cases all failed before repair. Expanding
through both reconciliation wrappers produces 30 cases. The first repaired
full suite caught an existing cancellation-result assertion: the live helper
ignored an obsolete error but its wrapper returned true. Propagating false
fixed the unchanged assertion; no test was skipped or weakened.

The second acceptance record is reset only after preserving the first verdicts
in Git. It remains pending while the wheel is rebuilt and verified.

## Verification

- All 172 UI tests pass, including 30 new late network/401/503 regressions.
- Source UI coverage is 96.93/86.58/95.71, above unchanged 95/86/93 floors.
- Repeated named fast Python spine: 1085 pass, three existing skips, 99.40s.
- Ruff check/format (765 files), docs and diff checks pass.
- First-candidate decision conformance: 184/184 killed, zero survived/invalid,
  baseline passed (96,869ms), source unchanged at that run. No Python decision
  implementation, mutation or selected Python test changed afterward; this is
  not described as a new post-JavaScript-repair mutation run.

## Follow-ups

AR-138 owns rebuilt-wheel browser proof and the second isolated acceptance
pass before PR #700 can merge. Native Windows and host activation are separate.

### Delivery receipt

Rebuilt-wheel proof at 2ecde1a5 passes all 21 loaded-view browser checks. All six
second-pass isolated verdicts satisfy that candidate; closure is 34680228.
PR #700 merged at 1ada216c208777630ec7162acf5a390f420fc0a4 on September 7,
05:28:53Z, read back as MERGED. Local main fast-forwarded cleanly. Hosted checks
were absent, not reported as passing; no bypass or exhaustive dispatch was used.
Current counts are 40 open trackers plus 97 unfinished legacy records (137).
