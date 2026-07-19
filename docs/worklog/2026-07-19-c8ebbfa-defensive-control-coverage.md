---
title: "Worklog detail: Cover defensive control branches"
status: active
category: worklog
created: 2026-07-19
updated: 2026-07-19
tags: [testing, coverage, windows, runtime-control]
related:
  - docs/roadmap/README.md
  - docs/worklog/2026-07-18-cbe9bc9-installed-control-transitions.md
supersedes: []
superseded_by: null
type: worklog
commit: c8ebbfafb59b6a8c6f4b38d86b6cbc655beed121
short: c8ebbfa
date: 2026-07-19
pr: null
related_issues:
  - docs/roadmap/issue-AR-100-wait-for-windows-dashboard-runtime-exit.md
  - docs/roadmap/issue-AR-101-enforce-restricted-global-master-switch.md
---

# Worklog detail: Cover defensive control branches

## Purpose

Exercise the final six statements left uncovered after the warning-strict full
suite completed at 99.98% line and branch coverage.

## Approach

Add exact regressions for non-brokerable master-read errors, inconsistent direct
master transitions, uncached authoritative reads, and the valid restricted
Windows host DACL shape with one restricting logon principal.

## Challenges encountered

The first two full-suite launches used Windows temporary roots that the product
correctly rejected as cross-account-substitutable. The authoritative run used
an owner-only fake home below Agency’s validated private root.

## Decisions and alternatives

No production branch was excluded or marked unreachable. Each defensive path is
covered through its public or narrow internal contract, preserving the 100%
line-and-branch release gate.

## Verification

- Warning-strict full non-performance suite: 5,847 passed, 19 skipped, 3 deselected.
- Aggregate production coverage after targeted append: 38,882 statements and 13,124 branches at 100.00%.
- Focused defensive regressions: 163 passed, 4 skipped.
- Ruff check, Ruff format, and diff checks passed.

## Follow-ups

Run performance, dashboard coverage, clean-artifact, installed-host, and hosted
CI gates before closing AR-100 and AR-101.
