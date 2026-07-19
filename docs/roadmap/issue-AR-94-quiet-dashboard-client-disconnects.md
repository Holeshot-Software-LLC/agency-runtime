---
title: "AR-94: Treat dashboard client disconnects as quiet transport completion"
status: in_progress
category: roadmap
created: 2026-07-18
updated: 2026-07-18
tags: [dashboard, reliability, networking, observability]
related:
  - docs/roadmap/issue-AR-12-installed-operations-dashboard.md
  - docs/roadmap/issue-AR-71-dashboard-accessible-truthful-states.md
  - docs/decisions/0029-secure-local-dashboard-and-bounded-observability.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: dashboard
issue_id: AR-94
priority: p1
tracker_url: "https://github.com/Holeshot-Software-LLC/agency-runtime/issues/95"
depends_on: [AR-12, AR-71]
blocks: []
---

# AR-94: Treat dashboard client disconnects as quiet transport completion

## Problem

A normal browser abort or navigation can raise a platform socket-disconnect
exception in the dashboard server. The handler logs a server failure, attempts
a second JSON error response on the dead socket, and produces another server
traceback.

## Current state

The request boundary now recognizes Windows and POSIX disconnect variants,
closes the abandoned connection quietly, and never performs the defensive
second write for that transport outcome. Genuine application failures still
log and attempt one bounded 500 response, while unrelated `OSError` values
propagate. Nineteen focused regressions and the 167-test dashboard-server lane
pass; a post-fix live abort canary and the repository-wide gates remain.

## Approach

Classify platform-equivalent disconnect errors as expected transport
termination, never retry a response write after the connection is gone, and
retain structured logging plus one bounded 500 response for genuine application
failures while the socket remains writable.

## Dependencies

AR-12 owns the installed dashboard and AR-71 owns truthful, accessible runtime
states.

## Acceptance

- [ ] Browser abort or navigation produces no application error log or traceback.
- [x] No second response write is attempted after a disconnect.
- [x] Genuine handler failures still return one bounded error when possible and are logged.
- [x] Windows and Linux disconnect exception variants are covered.
- [ ] Full statement and branch coverage plus live browser QA pass.
