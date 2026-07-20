---
title: "Isolate wall-clock performance gates"
status: active
category: worklog
created: 2026-07-20
updated: 2026-07-20
tags: [ci, testing, performance, portability]
related:
  - .github/workflows/ci.yml
  - tests/test_release_packaging.py
  - docs/roadmap/issue-AR-113-isolate-performance-gates.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: worklog
commit: 9d4e55b
short: 9d4e55b
date: 2026-07-20
pr: "https://github.com/Holeshot-Software-LLC/agency-runtime/pull/121"
related_issues:
  - docs/roadmap/issue-AR-113-isolate-performance-gates.md
---

# Worklog detail: Isolate wall-clock performance gates

## Purpose

Remove shared-runner timing noise from the Python compatibility matrix without
weakening the required routing and delegation performance gate.

## Approach

Exclude tests marked `performance` from every compatibility cell. Keep those
tests in the quality job's dedicated uninstrumented performance step, and add a
workflow contract assertion that protects this separation.

## Challenges encountered

Ubuntu Python 3.12 failed only the aggregate routing report's `passed` flag in a
shared-runner matrix cell. The same commit passed the dedicated uninstrumented
performance job, every completed compatibility cell, and all artifact and
security gates. The test's performance marker exposed that it was running in
both environments.

## Decisions and alternatives

Thresholds were not relaxed and the performance suite was not removed. Timing
is measured once in its purpose-built job; compatibility cells continue to run
all non-performance correctness tests under every supported Python version.

## Verification

The workflow contract suite passed 14/14. The dedicated routing performance
tests passed 2/2 locally. Documentation validation passed for 257 Markdown
files and `git diff --check` passed.

## Follow-ups

Complete the corrected hosted matrix and then mark AR-113 done.
