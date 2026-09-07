---
title: "Restore truthful bounded local verification"
status: active
category: worklog
created: 2026-09-07
updated: 2026-09-07
tags: [verification, workflow, cost, backlog]
related:
  - docs/roadmap/issue-AR-156-restore-cost-bounded-verification.md
  - docs/roadmap/acceptance/evidence/AR-156-verification-workflow-20260907.md
  - docs/decisions/0105-bound-delivery-to-live-demo-checkpoints.md
  - docs/decisions/0220-measure-dashboard-coverage-over-production-modules.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: worklog
commit: 9fb95136db78b05c73da3fbfddf12dc14c4f3827
short: 9fb95136
date: 2026-09-07
pr: null
related_issues:
  - docs/roadmap/issue-AR-156-restore-cost-bounded-verification.md
---

# Worklog detail: Truthful local verification

## Purpose and approach

Retain the implemented cost-bounded workflow while repairing false local success:
missing Node now fails before any selected gate runs. Listing remains passive.
Six new tests enter both local/hosted contract lists with exact membership parity.
The documented UI command now equals local/hosted production-only 95/86/93
arguments; no threshold, matrix membership, event or permission changes.
Stale direct-to-main and push guidance now agrees with current authority.

## Challenges and decisions

The broad check exposed an existing main-branch asset-budget regression:
387,355 bytes exceeded the unchanged strict 387,072-byte bound. Shortening
three full-line comments removes 297 bytes, with every non-comment JavaScript
byte unchanged. The resulting 14-byte margin is narrow and remains enforced.
Four Windows-profile assumptions also fail unchanged on Linux main; preserve
that receipt and leave native Windows work with the owner. Do not weaken its
loader guard or treat structural topology tests as hosted execution.

## Verification

Fresh workflow contracts: 165 pass, five Windows-named deselections, no skips
or failures (4.82s). Named production spine: 1085 pass, three existing skips
(68.41s). Full UI: 188 pass (250.23ms), production coverage 96.93/86.71/95.71.
Ruff passes over 766 Python files. Evidence records initial failures, reproduction
on untouched main and each repair. Exact rebuilt-wheel QA follows this clean
checkpoint; no fresh exhaustive corpus, matrix or native host claim.

## Follow-ups

AR-156 remains open with all thirteen criteria unchanged: native Windows/profile
and separately authorized hosted topology proof remain. The latest listed CI
run is an old cancelled August 31 run; current billing cause is unverified.
Finish bounded artifact QA and normal PR publication, then continue at AR-157.
