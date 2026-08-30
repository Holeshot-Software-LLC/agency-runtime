---
title: "AR-117: Parallelize PR verification without weakening coverage"
status: done
category: roadmap
created: 2026-07-21
updated: 2026-08-12
tags: [testing, ci, coverage, performance]
related:
  - .github/workflows/ci.yml
  - scripts/select_test_shard.py
  - tests/test_ci_sharding.py
  - docs/worklog/README.md
  - docs/decisions/0097-gate-expensive-ci-fanout-behind-quality-contracts.md
supersedes: []
superseded_by: null
type: issue
epic: testing
issue_id: AR-117
priority: p1
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/130
depends_on: [AR-113]
blocks: [AR-156]
---

# AR-117: Parallelize PR verification without weakening coverage

## Problem

The main quality job serializes lint, roughly seven thousand instrumented tests,
performance gates, and dashboard coverage. A small review fix therefore waits
about 45 minutes for feedback even though the independent checks can run safely
at the same time.

## Current state

Performance-marked tests are isolated from the compatibility matrix, but exact
Python coverage is still one monolithic job. Local iteration either repeats that
entire run or waits for the same serial bottleneck in hosted CI.

## Approach

Keep a fast required lane for lint, documentation and workflow contracts, and
dashboard coverage. Partition Python test files deterministically into four
size-balanced coverage jobs, upload each data file, combine them, and enforce
the unchanged 100% line-and-branch threshold. Run uninstrumented performance in
its own parallel job. Keep the complete compatibility and artifact matrices.
The seven-cell full compatibility matrix runs on `main` and by manual dispatch
instead of repeating for every PR edit; strict docs and tracker validation runs
in the fast PR lane.

ADR-0097 later refined this delivered topology after measured cost review. Fast
same-revision quality now gates expensive fanout, documentation history is
checked after a deliberate durable-head checkout, and the redundant Ubuntu
24.04/Python 3.13 serial cell is replaced by the exact four-shard coverage
union. Six serial compatibility cells retain supported-version and Windows
endpoint ordering evidence.

## Dependencies

AR-113 established that wall-clock performance belongs in a dedicated,
uninstrumented gate.

## Acceptance

- [x] Every non-performance test file belongs to exactly one deterministic coverage shard.
- [x] Four coverage shards run concurrently with isolated private runtime state.
- [x] Combined coverage still requires 100% line and branch coverage.
- [x] Lint, workflow/docs contracts, dashboard coverage, and performance run independently.
- [x] Workflow contract tests protect sharding, recombination, and the performance boundary.
- [x] The full compatibility matrix runs on `main` and manual dispatch, not every PR edit.
- [x] Hosted CI proves the parallel workflow and merge completes.
