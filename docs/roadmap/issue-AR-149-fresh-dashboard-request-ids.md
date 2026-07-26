---
title: "AR-149: Issue a fresh dashboard request ID per HTTP request"
status: open
category: roadmap
created: 2026-07-26
updated: 2026-07-26
tags: [dashboard, observability, http, traceability]
related:
  - docs/decisions/0027-authoritative-runtime-evidence-traces.md
  - docs/roadmap/issue-AR-142-instrument-runtime-boundaries.md
  - agency_runtime/server/dashboard.py
supersedes: []
superseded_by: null
type: issue
epic: observability
issue_id: AR-149
priority: p0
tracker_url: null
depends_on: []
blocks: []
---

# AR-149: Issue a fresh dashboard request ID per HTTP request

## Problem

The dashboard handler caches its content-free request ID on the long-lived
`BaseHTTPRequestHandler` instance. HTTP/1.1 keep-alive can therefore reuse one
ID for sequential requests on the same connection, collapsing otherwise
independent response, log, and Store-boundary traces.

## Current state

Single-request tests pass, but no regression sends two requests through one
`HTTPConnection`. The second request can inherit the first request's ID.

## Approach

Reset request-scoped state before every `handle_one_request` dispatch while
preserving one stable ID throughout that request. Prove the behavior over a real
keep-alive connection and retain the existing bounded, content-free format.

## Dependencies

AR-142 defines the cross-boundary instrumentation contract and ADR-0027 requires
evidence to remain attributable to the exact operation.

## Acceptance

- Sequential requests on one keep-alive connection receive distinct request IDs.
- Every boundary within one request uses the same ID.
- Response headers, error paths, and Store instrumentation remain correlated.
- The dashboard server and full warning-strict suites pass.

## Implementation evidence

Commit `6a3bdaa` resets request-scoped identity before each persistent-connection
dispatch, preserves that identity through the request, and correlates bounded
pre-dispatch protocol errors without echoing request content. A real keep-alive
regression proves sequential requests receive distinct IDs. The shared focused
package passed 168 Python tests with 3 skips, four post-review regressions, and
101 dashboard UI tests. Full current-artifact and warning-strict release gates
remain before closure.
