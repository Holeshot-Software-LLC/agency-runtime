---
title: "AR-88: Compare Agency modes against native host outcomes"
status: in_progress
category: roadmap
created: 2026-07-18
updated: 2026-07-20
tags: [evaluation, outcomes, delegation, comparison, evidence]
related:
  - docs/decisions/0076-bind-isolated-canaries-to-explicit-agency-modes.md
  - docs/roadmap/issue-AR-11-routing-evaluation-and-performance.md
  - docs/decisions/0030-versioned-quantitative-evaluation-gates.md
  - docs/decisions/0072-compare-task-outcomes-with-paired-trials.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: testing
issue_id: AR-88
priority: p0
tracker_url: "https://github.com/Holeshot-Software-LLC/agency-runtime/issues/89"
depends_on: [AR-11, AR-79, AR-87]
blocks: []
---

# AR-88: Compare Agency modes against native host outcomes

## Problem

Offline routing accuracy and contract tests do not prove that Agency improves
real task outcomes over a native host. The project must not make superiority
claims without paired, controlled, evidence-labelled comparisons.

## Current state

The strict content-free, model/router-aware comparison schema and paired
evaluator are implemented. They enforce evidence-class parity, report outcome
deltas and delegation regret without superiority claims, and cover the bounded
full-roster and lifecycle scenario corpus. Fresh paired installed-host trials
remain required.

## Approach

Pair identical scenario, trial, host, and model runs for native-only, Agency
observe/selection, preferred delegation, and strongly preferred delegation.
Measure completion, blinded quality, failed tests, escaped defects, duration,
cost, retries, duplicate work, merge conflicts, synthesis failure, supervisor
intervention, and delegation regret. Keep live-host, installed-isolated,
contract-only, and simulated evidence separate.

## Dependencies

AR-11 owns deterministic accuracy and performance gates. AR-79 owns installed
Codex evidence, and AR-87 owns the delegation variants being compared.

## Acceptance

- [x] Comparison observations are strict, bounded, content-free, and model/router-aware.
- [x] Exact scenario trials pair only matching hosts, evidence classes, and model identities.
- [x] Simulated, contract-only, and isolated evidence cannot support a live claim.
- [x] The evaluator reports outcome deltas and delegation regret without claiming superiority.
- [x] Full-roster direct, ambiguous, short, revised, adversarial, conflict, and abstention cases exist.
- [x] Provider failure, parent/child routing, authorization, decline, and Stop correction are covered.
- [ ] Installed hosts run fresh-session Agency-on and native-only trials where available.
- [x] Documentation labels every result by evidence maturity.
