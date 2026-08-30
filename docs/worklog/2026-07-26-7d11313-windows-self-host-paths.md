---
title: "Worklog detail: Bound Windows self-host paths"
status: active
category: worklog
created: 2026-07-26
updated: 2026-07-26
tags: [testing, windows, performance, process-containment]
related:
  - docs/roadmap/issue-AR-156-restore-cost-bounded-verification.md
  - docs/decisions/0030-versioned-quantitative-evaluation-gates.md
  - docs/decisions/0091-least-privilege-subprocess-environments.md
supersedes: []
superseded_by: null
type: worklog
commit: 7d11313
short: 7d11313
date: 2026-07-26
pr: null
related_issues:
  - docs/roadmap/issue-AR-156-restore-cost-bounded-verification.md
---

# Worklog detail: Bound Windows self-host paths

## Purpose

Eliminate the zero-output Windows self-host hang that invalidated complete
parallel-loop timing samples, while preserving a bounded deadline and proving
that forced runner termination reaps the actual worker process tree.

## Approach

The runner now rejects projected or prepared Windows runtime layouts when its
private interpreter or pytest base directory exceeds a conservative 240
character budget. Self-hosting tests allocate nested runtimes beneath a short,
owner-private directory derived from the active Agency CI root, independent of
the outer pytest temporary path. The integration timeout remains 60 seconds;
the repair does not hide the failure by widening it.

The crash-recovery regression now starts the runner in the real base
interpreter PID, launches an observable pytest child, terminates the runner,
and verifies that both identities exit before testing scratch recovery. Shared
bounded process-exit helpers replace duplicated test logic.

## Challenges encountered

An A/B test under the same private runtime isolated path geometry as the cause:
the short-root arm passed in 2.47 seconds, while the long-root arm reached its
180-second timeout without stdout or stderr. This ruled out the repository
lock, pipe backpressure, and owned-process containment as the primary cause.

## Verification

- Focused runner and containment package: 20 passed in 16.11 seconds.
- Both self-host integrations, invoked by the real private runtime with a long
  outer pytest temp path: 2 passed in 7.96 seconds.
- Ruff, format, and diff checks passed across all changed paths.
- The Windows path-budget unit test proves deterministic fail-closed rejection.

## Follow-ups

Capture green complete four-shard samples and a matched one-shard control before
making any speed claim. Use per-test duration evidence to rebalance only if the
slowest shard remains materially skewed.
