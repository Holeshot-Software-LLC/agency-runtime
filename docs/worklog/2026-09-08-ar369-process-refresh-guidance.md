---
title: "AR-369 distinguish process drift from stale installed files"
status: active
category: worklog
created: 2026-09-08
updated: 2026-09-08
tags: [installation, diagnostics]
related:
  - docs/roadmap/issue-AR-369-stale-host-process-serves-a-superseded-kernel.md
  - docs/roadmap/handoffs/issue-AR-369.md
supersedes: []
superseded_by: null
type: worklog
commit: null
short: null
date: 2026-09-08
pr: null
related_issues: [docs/roadmap/issue-AR-369-stale-host-process-serves-a-superseded-kernel.md]
---

# AR-369 distinguish process drift from stale installed files

## Purpose

Stop prescribing repeated no-op installs when only a running process differs
from the last published projection. This exact loop occurred in the parent.

## Approach

Correct only the warning and explanatory module text. Tell the operator what
was compared, guide normal integration/process reload and a fresh session, then
retain conditional host-specific installation guidance if mismatch persists.

## Challenges encountered

Installing identical published files cannot change an already-running process.
Hash inequality does not establish relative version age or installed-file
staleness. Do not broaden this correction into host restart automation.

## Decisions and alternatives

Preserve the existing advisory pointer and CLI package/disk drift checks.
Reject dynamic executable-pointer resolution or weakening kernel validation.
No new architectural policy; original AR-369 acceptance remains outstanding.

## Verification

39 warning-strict focused tests passed in 0.17 seconds. Seven new cases cover
five named hosts plus unnamed guidance, and same-pointer republication followed
by an actually changed running digest. No native/process restart performed.

## Follow-ups

Publish normally, then parent evaluates the combined installed candidate.
Original named-kernel and doctor/latest-binding requirements remain open.

Source checkpoint `a10e31170825b363a291e4cb346095887c6c6409` contains the bounded diagnostic correction and seven new regressions. Focused warning-strict execution passed 39 cases; no installed/native success is inferred.

Integration `5180c14f` retains completed fallback, timeout and reviewed resident recovery source plus their records. Independent capsule links and worklog rows were united; diagnostic source remains unchanged.
