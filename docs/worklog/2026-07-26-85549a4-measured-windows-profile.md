---
title: "Worklog detail: Add measured Windows shard profile"
status: active
category: worklog
created: 2026-07-26
updated: 2026-07-26
tags: [testing, windows, performance, evidence]
related:
  - docs/roadmap/issue-AR-156-restore-cost-bounded-verification.md
  - docs/decisions/0030-versioned-quantitative-evaluation-gates.md
supersedes: []
superseded_by: null
type: worklog
commit: 85549a4d8000aef708b7e1b90e3bcfb90a7d81b1
short: 85549a4
date: 2026-07-26
pr: null
related_issues:
  - docs/roadmap/issue-AR-156-restore-cost-bounded-verification.md
---

# Worklog detail: Add measured Windows shard profile

## Purpose

Replace Windows source-byte shard guesses with a reproducible, versioned
per-file duration profile derived only from clean all-green controls.

## Approach

Three explicit source-byte runs used one clean commit, exact 276-file union,
Python 3.13 runtime, four workers, and one independently verified assignment.
The strict generator validated each v2 artifact and computed the median
setup/call/teardown nanoseconds for every file. It wrote the fixed Windows
CPython profile path atomically; no weight was hand-edited.

Strict dry-run loads the resulting profile as `duration-lpt-v1/exact`. The
longest-processing-time schedule assigns 68, 69, 70, and 69 files with planned
median-duration totals separated by only 7.4801 ms. These planned totals are an
input hypothesis, not wall-clock speed evidence.

## Challenges encountered

An initial replacement series was discarded after its third arm exposed the
AR-158 observation-selection defect. The first two artifacts were not mixed
with later evidence. After the repair checkpoint, all three controls were
rerun from scratch and source-equivalence was enforced by the generator.

## Decisions and alternatives

Reusing diagnostic v1 output, mixing pre-fix and post-fix artifacts, manually
editing heavy-file weights, or claiming speed from theoretical shard totals
were rejected. ADR-0030 requires the committed profile to face matched wall
controls before it becomes the recommended loop.

## Verification

- Controls: 639.984, 657.689, and 639.573 seconds; median 639.984 seconds.
- Every control: 4/4 green, 276 files, 7,804 collected tests, clean `a34a9dc`.
- Profile SHA-256: `5415fc292a6b542bfd5491f183f177f95f57997636eacaa868dca3536489b4f3`.
- Strict dry-run: exact duration profile, four complete disjoint shards.
- Profile/runner/sharding package: 52 passed warning-strict.
- Documentation, Ruff, format, and diff checks passed.

## Follow-ups

Run matched strict-profile samples plus the one-worker source-byte control.
Recommend the parallel change loop only if measured median wall time improves
by at least AR-156's unchanged 30 percent threshold.
