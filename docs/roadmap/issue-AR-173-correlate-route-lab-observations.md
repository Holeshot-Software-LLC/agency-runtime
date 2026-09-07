---
title: "AR-173: Correlate Route Lab observations"
status: done
category: roadmap
created: 2026-07-27
updated: 2026-09-07
tags: [dashboard, routing, observability, traceability]
related:
  - docs/decisions/0232-represent-route-lab-observations-by-trace-digest.md
  - docs/decisions/0231-separate-route-lab-correlation-from-turn-persistence.md
  - docs/decisions/0105-bound-delivery-to-live-demo-checkpoints.md
  - docs/roadmap/issue-AR-404-evidence-led-backlog-completion.md
  - docs/roadmap/acceptance/evidence/AR-173-route-lab-correlation-20260907.md
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
The routing receipt and content-free HTTP observation share that trace through
a domain-separated digest, keeping bearer, prompt and task text out of logs.
The original claim of persisted routing evidence was incorrect: explain_route
has been diagnostic-only since e5f4a8c2, before this issue was written. Logs
are emitted; no turn or routing-decision rows should be created.

September 7 review adds a missing direct HTTP regression. Two real authenticated
social requests exercise the production explanation path with inference denied
by a test guard. Each trace is fresh UUIDv4, already bound before explanation,
and exactly joins its request-specific emitted observation. Allowed fields are
bounded and content-free; no diagnostic turn or routing rows appear. The first
focused pair passes, as do all 195 dashboard/explanation/observability tests,
204 UI tests/current coverage floors and the fresh named spine (1085 passes,
three existing skips). Full raw receipts are recorded. First verdicts are
preserved at 941b9025: criterion 2's original wording conflated raw trace and
digest. ADR-0232 explicitly supersedes ADR-0231 to clarify the representation.
All five criteria satisfy at 594bc4d3939d144440ae52f5acdf5f840c79f25e in the
second/final review, without copying earlier verdicts. AR-173 is done; no
runtime change, new trace field or third review. The owner paused before
publication: this accepted state is local to the unpushed AR-173 branch,
not main. Publish its normal PR only after an explicit continue request.

## Approach

Allocate correlation identity before the operation that persists domain
evidence. Update only the current request observation, pass the identity
explicitly through the service call, and test equality between the successful
response and the emitted request observation rather than merely testing UUID
shape.

## Dependencies

ADR-0027 requires unique and authoritative request traces. AR-142 instruments
runtime boundaries, AR-149 owns fresh HTTP request IDs, and AR-166 exposes safe
correlation receipts in the dashboard.

The existing pre-tracker exemption applies; no duplicate tracker is created.
ADR-0232 preserves ADR-0231's reconciliation of 1/4/5 and explicitly corrects
criterion 2's trace/digest wording. Only criterion 3 remains unchanged; all
original wording and the first contradicted verdict are preserved.

## Acceptance

- [x] Each admitted enabled Route Lab routing operation allocates one fresh
  UUIDv4 trace before explanation; invalid or disabled requests do not invent
  routing traces.
- [x] The route receipt carries the allocated trace ID, and the current HTTP
  observation's correlation_digest equals the domain-separated digest of that
  exact response trace; request ID remains a separate identity.
- [x] Correlation records remain content-free and bounded.
- [x] A real authenticated HTTP regression asserts exact emitted-observation
  digest-to-response-trace equality and no durable diagnostic turn/routing rows.
- [x] Focused dashboard HTTP, explanation and observability tests, UI/current
  coverage floors, named production spine, metadata, policy, worklog, strict
  docs/tracker, Ruff and diff checks pass; exhaustive integration is optional.

## Preserved original criteria

ADR-0231 reconciled 1/4/5 before first review; ADR-0232 additionally clarifies
the original criterion 2 after preserving the first verdict:

1. Each Route Lab request allocates one valid trace before routing.
2. The route receipt and current HTTP observation carry that exact trace.
4. A server regression asserts persisted observation-to-response equality.
5. The final repository release gate passes at the implementation commit.

The original narrative also claimed persisted routing evidence. That claim is
corrected rather than implemented: Route Lab has long been diagnostic-only.

## Implementation evidence

The new server regression posts two authenticated Route Lab requests through
the actual explanation code and checks fresh response-to-log equality. The
[receipt](acceptance/evidence/AR-173-route-lab-correlation-20260907.md) records
raw output and limits. All five isolated criteria satisfy at 594bc4d3.
