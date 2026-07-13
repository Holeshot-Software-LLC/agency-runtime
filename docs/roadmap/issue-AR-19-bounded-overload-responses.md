---
title: "AR-19: Deliver reliable bounded overload responses"
status: in_progress
category: roadmap
created: 2026-07-13
updated: 2026-07-13
tags: [http, windows, reliability, security, performance]
related:
  - docs/decisions/0041-bounded-asynchronous-overload-responses.md
  - docs/decisions/0017-sanitized-server-error-boundary.md
  - docs/decisions/0029-secure-local-dashboard-and-bounded-observability.md
  - docs/roadmap/issue-AR-17-production-hardening-portability.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: operations
issue_id: AR-19
priority: p0
tracker_url: "https://github.com/Holeshot-Software-LLC/agency-runtime/issues/20"
depends_on: []
blocks: [AR-17]
---

# AR-19: Deliver reliable bounded overload responses

## Problem

When the control API's bounded HTTP worker pool was saturated on Windows, the
server wrote a 503 Service Unavailable response and immediately closed the
socket while request bytes remained unread. Winsock could replace the response
with a TCP reset, so ordinary clients intermittently received a connection
abort instead of the documented overload response.

The synchronous rejection path could also spend up to half a second performing
socket I/O on the accept loop. Repeated slow connections could therefore delay
acceptance of unrelated requests even though normal request concurrency was
bounded.

## Current state

Normal request workers and overload-response workers now have independent hard
caps. A saturated request is handed to one of four daemon overload workers
without blocking the accept loop. The worker sends the fixed 503 response,
half-closes its response side, drains no more than the configured request-body
cap plus 64 KiB of framing for at most 250 ms, and then closes the connection.
Connections beyond the overload-worker cap are closed immediately.

## Approach

Keep the normal request semaphore authoritative. Add a small, fixed rejection
budget and acquire it without waiting. Follow the graceful TCP close sequence
inside that bounded worker while enforcing both a byte cap and an absolute
deadline so a slow or trickling client cannot retain the worker indefinitely.
Restore the rejection slot on every socket, close, and thread-start path.

## Dependencies

This bug was surfaced by AR-17's final warning-strict Windows validation and
extends AR-15's reliable rejection work to server-overload responses. It blocks
AR-17 until exact coverage, hosted Windows/Linux CI, review, and merge pass.

## Acceptance

- [x] Saturated ordinary requests receive 503 Service Unavailable with
      Retry-After: 1 reliably on Windows.
- [x] Overload response work cannot block the accept loop.
- [x] Overload threads, drain bytes, and drain wall time are hard-bounded.
- [x] Socket and thread-start failures restore all capacity.
- [x] A real saturated Windows connection delivers 503 after sending a
      one-megabyte request at the configured body limit.
- [ ] Warning-strict exact coverage and hosted Windows/Linux matrices pass.
- [ ] The reviewed fix is merged and tracker issue #20 is closed.
