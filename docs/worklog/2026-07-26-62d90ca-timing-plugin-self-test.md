---
title: "Worklog detail: Isolate timing plugin self-test"
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
commit: 62d90ca
short: 62d90ca
date: 2026-07-26
pr: null
related_issues:
  - docs/roadmap/issue-AR-156-restore-cost-bounded-verification.md
---

# Worklog detail: Isolate timing plugin self-test

## Purpose

Allow the timing plugin to measure its own regression suite without a test
temporarily corrupting the live measurement state between call and teardown.

## Approach

The repeated-configuration regression now applies its sentinel through a
nested monkeypatch context. That context restores the pre-existing plugin
state before the test function returns and before pytest emits the call-phase
report. The production plugin contract is unchanged.

## Challenges encountered

Instrumented run `14c20d874fb2e4287e47f999654af4af` reached 3 of 4 green
shards in 634.140 seconds before the test replaced the plugin's live module
state. The controller correctly recorded incomplete evidence and did not
publish a complete timing artifact. The run is preserved as rejected evidence,
not used in any speed comparison.

## Verification

- Repeated-configuration regression alone: 1 passed in 0.83 seconds.
- Complete runner test file under the active timing plugin: 27 passed in 22.37
  seconds, including a valid consolidated report.
- Documentation, Ruff, format, and diff checks passed.

## Follow-ups

Repeat the full instrumented 275-file corpus and derive weights only if all
four shards and the exact timing union validate.
