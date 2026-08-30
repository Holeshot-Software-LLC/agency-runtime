---
title: "Worklog detail: Use bounded test runtime homes"
status: active
category: worklog
created: 2026-07-26
updated: 2026-07-26
tags: [testing, windows, performance, isolation]
related:
  - docs/roadmap/issue-AR-156-restore-cost-bounded-verification.md
  - docs/decisions/0030-versioned-quantitative-evaluation-gates.md
supersedes: []
superseded_by: null
type: worklog
commit: 49aafe1
short: 49aafe1
date: 2026-07-26
pr: null
related_issues:
  - docs/roadmap/issue-AR-156-restore-cost-bounded-verification.md
---

# Worklog detail: Use bounded test runtime homes

## Purpose

Keep the change-loop contract tests valid when they execute inside the loop's
own deeply nested Windows shard directories, without weakening the product's
critical-path limit.

## Approach

Every test that constructs a valid parallel runtime now supplies the existing
short, owner-private runtime-home fixture to both projected geometry and any
fake runtime preparer. The explicit synthetic over-budget regression remains
unchanged, and the production 240-character guard is untouched.

## Challenges encountered

Run `5552d9c9102719741115319ce1e7b223` correctly rejected eight unit-test
runtime layouts that inherited the complete shard temporary path. Targeted
tests had passed from the shorter repository venv, so they did not previously
exercise that exact nesting. The run remains invalid for benchmark claims even
though its other three shards passed and its duration telemetry is useful for
diagnosis.

## Verification

- Normal complete change-loop test file: 19 passed in 16.08 seconds.
- Real private runtime with a 195-character outer base temp: 19 passed in 16.45
  seconds.
- Ruff, format, and diff checks passed.

## Follow-ups

Run one unchanged complete four-worker corpus and use its bounded duration
telemetry only after every shard succeeds.
