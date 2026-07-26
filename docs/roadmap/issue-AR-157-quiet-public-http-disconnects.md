---
title: "AR-157: Treat public HTTP client disconnects as transport completion"
status: open
category: roadmap
created: 2026-07-26
updated: 2026-07-26
tags: [http, reliability, networking, observability]
related:
  - docs/roadmap/issue-AR-94-quiet-dashboard-client-disconnects.md
  - docs/roadmap/issue-AR-142-instrument-runtime-boundaries.md
  - docs/decisions/0017-sanitized-server-error-boundary.md
  - docs/decisions/0027-authoritative-runtime-evidence-traces.md
  - docs/decisions/0029-secure-local-dashboard-and-bounded-observability.md
  - agency_runtime/server/http.py
  - agency_runtime/server/dashboard.py
  - tests/test_http_server.py
  - tests/test_dashboard_disconnects.py
supersedes: []
superseded_by: null
type: issue
epic: observability
issue_id: AR-157
priority: p1
tracker_url: null
depends_on: []
blocks: []
---

# AR-157: Treat public HTTP client disconnects as transport completion

## Problem

The public JSON server catches a response-write disconnect inside its broad
application boundary, logs it as an unhandled application failure, and attempts
a defensive 500 response on the same abandoned socket. The dashboard already
handles the equivalent transport outcome quietly, so the two HTTP surfaces
have inconsistent reliability and observability contracts.

## Current state

A complete four-shard test attempt reproduced Windows socket error 10053 after
the loopback client reached its bounded header timeout. The server completed
the expensive preflight after the client had closed, treated the failed write
as an application exception, and attempted a second write. Read-only review
found no shared Store, port, or temp-directory collision; this is a production
transport-boundary defect exposed by load, not the cause of preflight latency.

## Approach

Move the platform-equivalent disconnect classifier to one shared server module.
At both public HTTP dispatch boundaries, recognize a disconnect during the
primary response or defensive error response, close the connection, mark the
current observation `degraded/client_disconnected`, and perform no further
write or application-error log. Preserve structured logging and exactly one
bounded 500 attempt for genuine application failures while the connection is
still writable. Keep dashboard behavior equivalent through the shared helper.

## Dependencies

AR-94 establishes the dashboard behavior. AR-142 and ADR-0027 govern exact
runtime-boundary evidence; ADR-0017 and ADR-0029 govern sanitized, bounded HTTP
failure responses.

## Acceptance

- Public GET and POST response disconnects close quietly without a second write.
- A disconnect during the defensive 500 is also quiet and bounded.
- Expected Windows and POSIX disconnect variants share one classifier across
  public HTTP and dashboard surfaces.
- The affected observation is marked `degraded/client_disconnected` without
  logging private request content.
- Genuine application failures still log and attempt exactly one sanitized 500.
- Focused HTTP, dashboard-disconnect, coverage, and warning-strict gates pass.

## Implementation evidence

Pending implementation and current-head verification. Tracker creation remains
pending explicit outward authorization.
