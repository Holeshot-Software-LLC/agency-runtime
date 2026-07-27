---
title: "AR-144: Restore dashboard UI release coverage gate"
status: done
category: roadmap
created: 2026-07-26
updated: 2026-07-27
tags: [dashboard, ui, testing, coverage, release]
related:
  - tests/dashboard_ui.test.mjs
  - docs/roadmap/issue-AR-138-coherent-observable-dashboard-ui.md
  - docs/RELEASE_CHECKLIST.md
supersedes: []
superseded_by: null
type: issue
epic: dashboard
issue_id: AR-144
priority: p0
tracker_url: null
depends_on:
  - AR-138
blocks: []
---

# AR-144: Restore dashboard UI release coverage gate

## Problem

The dashboard interaction suite passed every existing test while the exact
release command failed its 96 percent function-coverage floor. Bound startup,
navigation, provider, workforce, hash-change, Route Lab error, worker-detail,
and notice-expiry callbacks could therefore regress without failing the release
gate.

## Current state

The initial exact release run passed 82 tests but measured 95.00 percent lines,
90.74 percent branches, and 92.95 percent functions. The coverage command
correctly rejected the result; no threshold was changed.

## Approach

Exercise the real bound callbacks through the existing dashboard harness,
including successful and failed asynchronous paths and the notice timer. Keep
the tests behavioral so they assert user-visible state and lifecycle cleanup
instead of merely invoking uncovered functions.

## Dependencies

AR-138 owns dashboard coherence and accessibility behavior. The release
checklist owns the fixed coverage floors.

## Acceptance

- The exact dashboard release-coverage command exits successfully.
- Line coverage is at least 95 percent, branch coverage at least 90 percent,
  and function coverage at least 96 percent.
- Navigation, startup, provider, workforce, Route Lab, worker-detail, and
  notice-expiry callbacks have behavioral assertions.
- Coverage thresholds and production behavior are unchanged.

## Implementation evidence

The repaired suite passes all 84 tests with 97.13 percent lines, 91.28 percent
branches, and 96.32 percent functions under the exact release command. The
tests cover bound callbacks and both success and failure presentation; no
production code or threshold changed. Tracker creation remains pending explicit
outward-action authorization.
