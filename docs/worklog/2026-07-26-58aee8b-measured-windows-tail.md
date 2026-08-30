---
title: "Worklog detail: Measure and trim the Windows tail"
status: active
category: worklog
created: 2026-07-26
updated: 2026-07-26
tags: [testing, windows, performance, instrumentation]
related:
  - docs/roadmap/issue-AR-156-restore-cost-bounded-verification.md
  - docs/decisions/0030-versioned-quantitative-evaluation-gates.md
supersedes: []
superseded_by: null
type: worklog
commit: 58aee8b
short: 58aee8b
date: 2026-07-26
pr: null
related_issues:
  - docs/roadmap/issue-AR-156-restore-cost-bounded-verification.md
---

# Worklog detail: Measure and trim the Windows tail

## Purpose

Replace byte-size guesses with trustworthy per-file duration evidence so the
local Windows change loop can balance its four shards and shorten production
feedback without hiding tests.

## Approach

The runner now offers an opt-in file-timing mode. A small explicit pytest
plugin records setup, call, and teardown duration for every planned file into
owner-private shard reports. The controller validates run identity, shard
identity, exact path membership, totals, bounds, and successful shard state
before publishing one consolidated artifact. Default execution is unchanged.

Several broad doctor and smoke fixtures were also narrowed to the contract each
test actually exercises. One real generated Hermes adapter remains in the
operator-profile isolation test, while unrelated host and network work is
stubbed by dedicated seams whose real behavior is covered elsewhere.

## Challenges encountered

The first valid full four-worker baseline took 676.50 seconds. Its file-count
shards differed by 173.61 seconds from fastest to slowest, demonstrating that
source bytes are not a useful Windows runtime proxy. Independent review also
found that an early timing draft could publish red-run evidence and could
resolve pytest paths against the wrong root; both paths now fail closed and
have regressions.

## Verification

- First valid uninstrumented baseline: run
  `411b67385c033451c78f632ecc5fc867`, 4 of 4 shards passed, 676.50 seconds.
- Focused runner, sharding, doctor, and smoke-isolation suite: 46 passed in
  43.87 seconds.
- Release-packaging suite: 57 passed in 7.13 seconds.
- Release hygiene checked 1,282 files successfully.
- Documentation metadata, policy availability, worklog, and repository docs
  checks passed.
- Ruff, format, and diff checks passed.

## Follow-ups

Collect a valid instrumented corpus, derive versioned Windows weights from its
exact file timings, and compare three matched warm four-worker runs with the
one-worker control before making a speed claim or closing AR-156.
