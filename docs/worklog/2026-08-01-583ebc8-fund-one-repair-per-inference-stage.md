---
title: "Worklog detail: Fund one repair per inference stage"
status: active
category: worklog
created: 2026-08-01
updated: 2026-08-01
tags: [workforce, inference, configuration, budgets, regression]
related:
  - docs/roadmap/issue-AR-218-fund-one-repair-per-inference-stage.md
  - docs/roadmap/issue-AR-217-bind-gap-evidence-to-hiring-critics.md
  - docs/decisions/0114-fund-one-default-workforce-semantic-repair.md
  - docs/decisions/0132-fund-one-repair-per-workforce-inference-stage.md
supersedes: []
superseded_by: null
type: worklog
commit: 583ebc8
short: 583ebc8
date: 2026-08-01
pr: null
related_issues:
  - docs/roadmap/issue-AR-218-fund-one-repair-per-inference-stage.md
---

# Worklog detail: Fund one repair per inference stage

## Purpose

Repair the exact product boundary where the default fast workforce budget could
correct either planner or recruiter inference, but not both in one route. The
consumed `8cfd975` trial used its third and final call on the first recruiter
response after repairing the planner, leaving the recruiter's already bounded
correction unreachable.

## Approach

Fresh fast-mode defaults now fund four total calls. The existing planner and
recruiter loops still permit only one correction each; no retry loop or
deterministic staffing branch changed. Bundled YAML, the typed dataclass, raw
loader fallback, partial configuration validation, hook-timeout proof, and the
curated mutation agree on the new default. Explicit persisted lower values stay
operator-owned.

## Challenges encountered

Earlier tests covered the two recovery shapes independently: planner repair
with a valid recruiter, and valid planner with recruiter repair. Both passed in
three calls and therefore hid the composed four-call requirement. The new test
reproduces the exact live ordering in a single route.

## Decisions and alternatives

ADR-0132 supersedes ADR-0114's one-shared-repair default. Spending outside the
published cap, skipping planner validation, and filling recruiter output
deterministically were rejected because they weaken bounded execution or
inference ownership.

## Verification

- Exact composed regression and default/override/timeout checks: 5 passed.
- Focused inference, configuration, installer, and decision tests: 250 passed,
  1 skipped.
- Named Python production spine: 643 passed, 6 skipped.
- Dashboard UI: 110 passed.
- Documentation: 612 Markdown files validated.
- Routing evaluation: every correctness, performance, scale, and startup gate
  passed.
- Decision conformance: baseline passed; 73/73 mutations killed, zero survived
  or invalid, and `source_unchanged=true`.
- Two bounded review passes found no production defect; one stale metadata date
  was corrected.
- Repository-wide Ruff lint/format and `git diff --check` passed.

## Follow-ups

Run the named local fast gate once, obtain exact-head review, merge and install
the exact revision, deliberately raise this machine's persisted fast budget to
four, then run one activation and at most one README product trial. Stop and
publish the evidence page if that trial finds a new first boundary.
