---
title: "AR-173: Correlate Route Lab observations"
status: in_progress
category: roadmap
created: 2026-07-27
updated: 2026-07-27
tags: [dashboard, routing, observability, traceability]
related:
  - docs/decisions/0027-authoritative-runtime-evidence-traces.md
  - docs/roadmap/issue-AR-142-instrument-runtime-boundaries.md
  - docs/roadmap/issue-AR-149-fresh-dashboard-request-ids.md
  - docs/roadmap/issue-AR-166-truthful-dashboard-disclosure-and-correlation.md
  - agency_runtime/server/dashboard.py
  - tests/test_dashboard.py
supersedes: []
superseded_by: null
type: issue
epic: observability
issue_id: AR-173
priority: p1
tracker_url: null
depends_on: [AR-142, AR-149, AR-166]
blocks: []
---

# AR-173: Correlate Route Lab observations

## Problem

The dashboard Route Lab created a routing trace inside `explain_route`, but the
HTTP request observation had already been created without that trace identity.
The successful response therefore displayed a route receipt that could not be
joined back to the request-boundary observation used for debugging.

## Current state

The handler creates one UUID trace before routing, correlates the current
request observation with it, and passes that exact value into `explain_route`.
The returned routing receipt, persisted routing evidence, and content-free HTTP
observation now share the same trace identity while keeping the bearer, prompt,
and task text out of request logs.

## Approach

Allocate correlation identity before the operation that persists domain
evidence. Update only the current request observation, pass the identity
explicitly through the service call, and test equality between the successful
response and the stored request observation rather than merely testing UUID
shape.

## Dependencies

ADR-0027 requires unique and authoritative request traces. AR-142 instruments
runtime boundaries, AR-149 owns fresh HTTP request IDs, and AR-166 exposes safe
correlation receipts in the dashboard.

Tracker creation remains pending explicit outward-write authorization.

## Acceptance

- [x] Each Route Lab request allocates one valid trace before routing.
- [x] The route receipt and current HTTP observation carry that exact trace.
- [x] Correlation records remain content-free and bounded.
- [x] A server regression asserts persisted observation-to-response equality.
- [ ] The final repository release gate passes at the implementation commit.

## Implementation evidence

The focused dashboard server test posts one authenticated Route Lab request,
then proves its response trace equals the trace digest on the corresponding
request observation. Final aggregate evidence is recorded after the complete
release gate.
