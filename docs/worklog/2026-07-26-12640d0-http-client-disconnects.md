---
title: "Worklog detail: Stop after HTTP client disconnects"
status: active
category: worklog
created: 2026-07-26
updated: 2026-07-26
tags: [http, reliability, networking, observability]
related:
  - docs/roadmap/issue-AR-157-quiet-public-http-disconnects.md
  - docs/roadmap/issue-AR-94-quiet-dashboard-client-disconnects.md
  - docs/decisions/0017-sanitized-server-error-boundary.md
  - docs/decisions/0027-authoritative-runtime-evidence-traces.md
  - docs/decisions/0029-secure-local-dashboard-and-bounded-observability.md
supersedes: []
superseded_by: null
type: worklog
commit: 12640d0
short: 12640d0
date: 2026-07-26
pr: null
related_issues:
  - docs/roadmap/issue-AR-157-quiet-public-http-disconnects.md
---

# Worklog detail: Stop after HTTP client disconnects

## Purpose

Make public API response aborts behave as expected transport completion instead
of application failures that log private internals and attempt a second write
to an already abandoned socket.

## Approach

One shared server helper classifies built-in, POSIX errno, and Windows Winsock
disconnect variants. The public handler now closes expected disconnects during
the primary response without logging or retrying. A guard inside each active
GET/POST runtime boundary also catches a disconnect during the one defensive
500, marks the request `degraded/client_disconnected`, and stops. The outer
handler remains a quiet fallback for parser and other pre-dispatch I/O.

Dashboard handlers inherit the same classifier and close behavior while
retaining their request-ID lifecycle. Unrelated OS errors still propagate;
genuine application defects still log once and attempt exactly one sanitized
500 response.

## Challenges encountered

Closing only at `handle_one_request` would suppress the traceback but allow the
runtime observation context to exit first. Keeping the defensive-write guard
inside the request boundary preserves the exact degraded outcome on both HTTP
surfaces.

## Verification

- Public and dashboard disconnect suites: 26 passed.
- Complete focused HTTP and dashboard server package: 154 passed, 3 skipped in
  75.41 seconds.
- Ruff, format, and diff checks passed across all five changed paths.

## Follow-ups

Run the complete instrumented four-worker corpus. Retain the 15-second loaded
loopback test budget separately from this production transport repair.
