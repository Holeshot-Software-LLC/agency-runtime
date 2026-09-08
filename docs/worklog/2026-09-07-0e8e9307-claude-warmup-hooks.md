---
title: "AR-410 native-only Claude warm-up hook suppression"
status: active
category: worklog
created: 2026-09-07
updated: 2026-09-07
tags: [claude, canary, performance]
related:
  - docs/roadmap/issue-AR-410-disable-claude-warmup-staffing.md
  - docs/decisions/0237-isolate-claude-bootstrap-from-agency-evaluation.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: worklog
commit: 0e8e9307
short: 0e8e9307
date: 2026-09-07
pr: null
related_issues: [docs/roadmap/issue-AR-410-disable-claude-warmup-staffing.md]
---

# AR-410 native-only Claude warm-up hook suppression

## Purpose

Prevent bootstrap from spending Agency inference capacity before the real
nonce-bound canary. Exactly four product lines add the supported session-only
disableAllHooks setting to warm-up argv, never the actual request.

## Approach

Preserve plugin registration, first-session warm-up, control authority, safe
permissions, deadline and exact live proof. No owner configuration is changed.

## Challenges encountered

The first uncommitted approach toggled the disposable private master. Independent
review found installed hooks explicitly bind the owner's control path, defeating
that change despite 40 passing doubled tests. It was discarded entirely.
Corrected tests initially called the generator with the wrong argument name,
then assumed shell-command shape instead of command plus args. Those fixture
errors produced two runs of 1 failed/60 passed; both were corrected.

## Decisions and alternatives

ADR-0237 records warm-up-only native hook suppression. Managed policy may
override session settings; do not change policy or treat simulation as live proof.

## Verification

Final focused seven tests passed in 0.22s; focused Ruff and diff checks passed.
Independent second review and installed changed-candidate live evidence were
still pending when this source checkpoint was committed for parallel build.

## Follow-ups

AR-410 remains in_progress. Complete records/tracker parity, independent review,
isolated acceptance and exact-installed native evidence without changing proof.
