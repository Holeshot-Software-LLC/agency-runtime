---
title: "Worklog detail: Harden parallel-loop self-hosting"
status: active
category: worklog
created: 2026-07-26
updated: 2026-07-26
tags: [testing, security, performance, process-containment]
related:
  - docs/roadmap/issue-AR-156-restore-cost-bounded-verification.md
  - docs/decisions/0030-versioned-quantitative-evaluation-gates.md
  - docs/decisions/0091-least-privilege-subprocess-environments.md
supersedes: []
superseded_by: null
type: worklog
commit: d2ab19b
short: d2ab19b
date: 2026-07-26
pr: null
related_issues:
  - docs/roadmap/issue-AR-156-restore-cost-bounded-verification.md
---

# Worklog detail: Harden parallel-loop self-hosting

## Purpose

Make the private parallel test runtime capable of exercising its own runner
without trusting ambient import paths, and preserve actionable evidence when a
loaded integration test exceeds its deadline.

## Approach

The runtime-contract protocol is now version 2. Its owner-trusted receipt
records the exact dependency bridge selected by the invoking interpreter. A
pytest process already running inside the private environment can recover the
verified loaded package root; a direct nested runner can recover the bridge
only when the current interpreter, private runtime root, runtime owner receipt,
contract receipt, and bounded runtime receipt agree. Ambient `PYTHONPATH`
remains excluded.

Optimization-sensitive `assert` statements were replaced with explicit
runtime validation across the production package and scripts, and the
regression now scans both surfaces. Failed nested-shard assertions retain a
bounded diagnostic tail. Loaded child-process and loopback HTTP integration
budgets were widened after full-load evidence showed exact deadline expiry;
passing tests remain unaffected. Each shard now reports its 25 slowest tests
to support a later evidence-based rebalance.

## Challenges encountered

The first full run exposed that sysconfig inside the intentionally empty
private venv cannot rediscover pytest supplied by the explicit dependency
bridge. Recovering only an already-loaded pytest package fixed in-process
self-hosting but not direct child invocations. The final protocol therefore
binds the bridge to protected runtime receipts rather than an environment
string.

Two later full runs rejected their timing evidence. Under the complete loaded
corpus, nested dummy pytest children hit their exact 60-second deadline with no
output and a loopback HTTP client hit its exact 5-second header deadline. The
same nested tests passed alone and in four simultaneous focused stress copies,
supporting bounded load sensitivity rather than an assertion, isolation, or
containment failure. No failed sample is used for a speed claim.

## Verification

- Focused repair package: 223 passed in 26.42 seconds.
- Final receipt and self-host regression slice: 16 passed in 4.71 seconds.
- Ruff, format, and diff checks passed across all changed paths.
- Failed full samples remain explicitly rejected pending green reruns.

## Follow-ups

Run at least two green complete warm corpora, capture the new slow-test output,
and compare a successful current-head four-shard arm with a matched one-shard
arm. Keep local latency evidence separate from hosted runner-minute savings.
