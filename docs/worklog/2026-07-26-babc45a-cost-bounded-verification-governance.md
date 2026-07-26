---
title: "Worklog detail: Govern cost-bounded verification"
status: active
category: worklog
created: 2026-07-26
updated: 2026-07-26
tags: [testing, ci, performance, cost]
related:
  - docs/roadmap/issue-AR-117-parallelize-pr-verification.md
  - docs/roadmap/issue-AR-156-restore-cost-bounded-verification.md
  - docs/decisions/0030-versioned-quantitative-evaluation-gates.md
supersedes: []
superseded_by: null
type: worklog
commit: babc45a
short: babc45a
date: 2026-07-26
pr: null
related_issues:
  - docs/roadmap/issue-AR-117-parallelize-pr-verification.md
  - docs/roadmap/issue-AR-156-restore-cost-bounded-verification.md
---

# Worklog detail: Govern cost-bounded verification

## Purpose

Record the regression that restored seven complete compatibility runs to every
pull-request edit and govern both the hosted-cost repair and a faster isolated
local change loop.

## Approach

AR-156 preserves AR-117's existing policy: pull requests run the complete
non-performance corpus through coverage plus all other production gates, while
the unchanged seven-cell compatibility matrix runs on `main` and manual
dispatch. It also defines a four-process local runner that reuses the canonical
file sharding and private-runtime boundaries without replacing the serial
release command before parity and timing are proven.

## Challenges encountered

Recent GitHub Actions jobs terminate before executing any step because the
account reports a payment or spending-limit problem. Their failures cannot be
used as code evidence, so the issue separates static and local acceptance from
the later hosted canary.

## Decisions and alternatives

Optimizing dependency installation was rejected as the primary remedy because
sampled test bodies consumed 451-1,704 seconds while installation consumed only
6-25 seconds. Weakening the complete compatibility matrix was also rejected;
only its already-governed event cadence is restored.

## Verification

- Two successful PR runs were compared at 23.33 and 119.12 raw runner-minutes.
- Current workflow, history, AR-117, North Star, and packaging-contract tests
  were traced read-only.
- Documentation validation passed for 397 Markdown files.
- `git diff --check` passed.

## Follow-ups

Implement and measure AR-156. Hosted completion remains dependent on repairing
the external GitHub Actions billing or spending state.
