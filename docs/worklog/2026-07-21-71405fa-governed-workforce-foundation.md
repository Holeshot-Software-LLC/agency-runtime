---
title: "Establish the governed workforce foundation"
status: active
category: worklog
created: 2026-07-21
updated: 2026-07-21
tags: [workforce, recruitment, staffing, contractors, lifecycle]
related:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-120-normalized-workforce-recruitment-index.md
  - docs/roadmap/issue-AR-121-inference-planning-and-staffing.md
  - docs/roadmap/issue-AR-122-contractor-hiring-and-lifecycle.md
  - docs/decisions/0080-plan-before-recruiting-from-the-whole-workforce.md
  - docs/decisions/0081-compile-contractors-from-governed-structured-contracts.md
  - docs/decisions/0082-schedule-assurance-by-artifact-lifecycle.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: worklog
commit: 71405fad649afe9f8bdd75cbe50304c35c98b194
short: 71405fa
date: 2026-07-21
pr: https://github.com/Holeshot-Software-LLC/agency-runtime/pull/129
related_issues:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-120-normalized-workforce-recruitment-index.md
  - docs/roadmap/issue-AR-121-inference-planning-and-staffing.md
  - docs/roadmap/issue-AR-122-contractor-hiring-and-lifecycle.md
---

# Worklog detail: Establish the governed workforce foundation

## Purpose

Replace loosely coupled roster labels with an exact, auditable workforce model
that can support inference-first planning, deterministic staffing, temporary
contractors, stable employee identity, and lifecycle-bound performance evidence.

## Approach

Project every governed agent into a versioned recruitment contract and a compact
whole-roster index that keeps disabled workers visible. Bind inferred work plans
and recruitment proposals to exact plan and roster hashes, then independently
recompute eligibility, capability coverage, minimal teams, composition rules,
delegation contexts, and assurance sequencing. Add immutable worker identity,
version lineage, hiring evidence, lifecycle events, and activation-bound outcome
records to the canonical SQLite store. Compile new contractors only from closed
employment contracts and fixed templates; include nine narrowly scoped initial
contractors with nearest-neighbor hard negatives.

## Challenges encountered

The first warning-as-error integration pass exposed SQLite connections opened by
new tests with transaction-only context managers. The tests now explicitly close
every connection while preserving commits for migration and receipt fixtures.
The complete workforce index also needed compact positional serialization to put
all 263 workers in one bounded inference request without omitting disabled
semantic winners.

## Decisions and alternatives

Worker identity is stable while prompt revisions remain immutable lineage.
Disabling is an activation overlay rather than an employment state, so operators
can see which stronger candidate they chose to leave unavailable. Recruitment
model claims are advisory: deterministic verification recomputes the executable
team and atomically abstains on drift, weak coverage, conflicts, excess staffing,
or missing independent assurance. These boundaries implement ADR-0080 through
ADR-0082.

## Verification

- Focused workforce, configuration, roster, store, retention, and migration gate:
  473 passed and 3 platform-specific skips with warnings treated as errors.
- Ruff formatting and lint passed for every changed Python file.
- Git diff whitespace validation passed.

## Follow-ups

AR-121 still owns live inference transport and preflight integration. AR-122
still owns the governed hiring pipeline and promotion policy. AR-123 through
AR-125 retain the CLI/dashboard, native-host, and comprehensive evaluation work.
