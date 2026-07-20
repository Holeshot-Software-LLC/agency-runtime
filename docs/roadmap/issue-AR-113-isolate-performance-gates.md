---
title: "AR-113: Isolate wall-clock performance gates from the compatibility matrix"
status: done
category: roadmap
created: 2026-07-20
updated: 2026-07-20
tags: [testing, ci, performance, portability]
related:
  - .github/workflows/ci.yml
  - tests/test_release_packaging.py
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: testing
issue_id: AR-113
priority: p0
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/119
depends_on: []
blocks: []
---

# AR-113: Isolate wall-clock performance gates from the compatibility matrix

## Problem

The Python compatibility matrix runs every test, including tests explicitly
marked `performance`. Those tests enforce wall-clock latency and concurrency
thresholds. Shared-runner load caused Ubuntu Python 3.12 in PR #118 to fail the
routing latency report while its dedicated uninstrumented performance job and
all completed correctness, artifact, portability, and security jobs passed.

## Current state

The quality job already runs performance-marked tests once in a dedicated,
uninstrumented step after exact correctness coverage. The compatibility matrix
duplicates those timing gates under seven different shared-runner load profiles,
making compatibility success depend on transient machine scheduling.

## Approach

Exclude `performance`-marked tests from each Python compatibility cell. Keep the
dedicated uninstrumented performance step unchanged and required. Extend the CI
workflow contract test so the matrix cannot silently resume running wall-clock
gates.

## Dependencies

AR-11 owns the quantitative routing and performance thresholds. AR-104 owns the
trusted hosted portability matrix.

## Acceptance

- [x] Every Python compatibility cell excludes performance-marked tests.
- [x] The dedicated uninstrumented performance step remains required.
- [x] A workflow contract test protects the separation.
- [x] The corrected complete hosted matrix passes.
- [x] Documentation, worklog, and tracker mappings remain synchronized.

PR #121 passed the complete corrected matrix: Ubuntu Python 3.10-3.14,
Windows Python 3.10 and 3.14, exact line and branch coverage, the unchanged
dedicated routing/delegation performance tests, dashboard UI coverage,
portability contracts, deterministic source audit, Windows/Linux artifact
build, byte parity and smoke, dependency review, and CodeQL. The previously
failing Ubuntu Python 3.12 cell passed in 7m46s without running wall-clock tests.
