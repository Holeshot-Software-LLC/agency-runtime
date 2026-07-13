---
title: "AR-15: Deliver reliable JSON rejection responses on Windows"
status: done
category: roadmap
created: 2026-07-11
updated: 2026-07-12
tags: [dashboard, http, windows, reliability, security]
related:
  - docs/decisions/0017-sanitized-server-error-boundary.md
  - docs/decisions/0029-secure-local-dashboard-and-bounded-observability.md
supersedes: []
superseded_by: null
type: issue
epic: operations
issue_id: AR-15
priority: p1
tracker_url: "https://github.com/Holeshot-Software-LLC/agency-runtime/issues/15"
depends_on: []
blocks: [AR-07]
---

# AR-15: Deliver reliable JSON rejection responses on Windows

## Problem

An authenticated POST with a non-JSON content type could intermittently abort
its Windows TCP connection before the client received the intended `415` JSON
response. The server rejected the request correctly, but closed the socket with
the small request body still unread. Windows could translate that close into a
reset, hiding the actionable error from CLI and dashboard clients.

The HTTP server fixture also wrote a POSIX-only `/dev/null` configuration path
into the process environment without restoring it, weakening Windows isolation
and making later tests order-dependent.

## Current state

Both authenticated HTTP surfaces consume a rejected request body only when its
declared length is valid and within the configured request limit. Malformed or
oversized lengths fail closed without an unbounded read. The JSON error is then
delivered reliably on Windows. HTTP fixtures use pytest-managed temporary
configuration and restore the configuration cache after shutdown.

## Approach

Keep authentication and origin checks ahead of body handling. After those
checks pass, drain a small body before returning an unsupported-media response.
Share the bounded drain in the base HTTP handler so the control API and
operations dashboard have the same transport behavior. Exercise each rejection
repeatedly against real loopback servers and parse every returned JSON body.

## Dependencies

This is a contained reliability and security-boundary fix. It blocks `AR-07`
because production readiness cannot accept an intermittent loss of an
authenticated API error response.

## Acceptance

- [x] Authenticated non-JSON POSTs return `415` with a parseable JSON body on
  the dashboard and control API.
- [x] Rejected bodies are consumed only within the configured request limit.
- [x] Malformed or oversized lengths do not trigger an unbounded read.
- [x] Windows HTTP tests use temporary, pytest-managed configuration paths.
- [x] Repeated real-loopback regressions pass without connection aborts.

## Verification

- `tests/test_dashboard.py::test_dashboard_post_requires_json_content_type`
  performs ten authenticated rejection round trips against the real dashboard
  server.
- `tests/test_http_server.py::test_non_json_post_is_rejected` performs the same
  repeated response-body check against the control API.
- The combined dashboard and HTTP server files pass on native Windows.
