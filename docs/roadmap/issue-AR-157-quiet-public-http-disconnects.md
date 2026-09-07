---
title: "AR-157: Treat public HTTP client disconnects as transport completion"
status: done
category: roadmap
created: 2026-07-26
updated: 2026-09-07
tags: [http, reliability, networking, observability]
related:
  - docs/roadmap/acceptance/issue-AR-157.md
  - docs/roadmap/issue-AR-404-evidence-led-backlog-completion.md
  - docs/roadmap/acceptance/evidence/AR-157-http-disconnects-20260907.md
  - docs/decisions/0105-bound-delivery-to-live-demo-checkpoints.md
  - docs/worklog/README.md
  - docs/roadmap/issue-AR-94-quiet-dashboard-client-disconnects.md
  - docs/roadmap/issue-AR-142-instrument-runtime-boundaries.md
  - docs/decisions/0017-sanitized-server-error-boundary.md
  - docs/decisions/0027-authoritative-runtime-evidence-traces.md
  - docs/decisions/0029-secure-local-dashboard-and-bounded-observability.md
  - agency_runtime/server/http.py
  - agency_runtime/server/http_transport.py
  - agency_runtime/server/dashboard.py
  - tests/test_http_server.py
  - tests/test_http_disconnects.py
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

September 7 review confirms the existing 12640d0 repair remains implemented.
GET/POST primary and defensive-response disconnects close quietly inside their
observation boundary; the shared classifier recognizes built-ins, POSIX errno
and Winsock code representations without suppressing unrelated errors.
Genuine application faults retain one sanitized log and one bounded 500 attempt.

Two strengthened primary-disconnect tests exercise real boundary emission with
private query/body/error sentinels: exact http operation, degraded outcome and
client_disconnected reason are recorded without content leakage or retries.
The full focused package passes 104 tests with three existing inference skips
in 22.25s; shared transport coverage is 100 percent (11 statements/four branches).
Its two stale HTTP fixtures are repaired without runtime changes: current stored
catalog cardinality replaces a fixed 14, and the resident-worker rejection case
seeds one real suggestion then requires complete evidence equality after rejection.
Both failures reproduce on unchanged main before repair.

All runtime/scripts bytes equal the recent clean dccb4e85 wheel, supporting
explicit reuse of its 21 loaded-browser checks and current named-spine receipt.
Only the obsolete sixth verification criterion is reconciled under ADR-0105;
the first five remain unchanged. All six isolated criteria satisfy at a35657e1
on September 7; exact run IDs and digests are in the acceptance record. AR-157
is done, with normal PR publication next and no duplicate legacy tracker.

## Historical trigger

A complete four-shard test attempt reproduced Windows socket error 10053 after
the loopback client reached its bounded header timeout. The server completed
the expensive preflight after the client had closed, treated the failed write
as an application exception, and attempted a second write. Read-only review
found no shared Store, port, or temp-directory collision; this is a production
transport-boundary defect exposed by load, not the cause of preflight latency.

## Approach

Publish current verification and the bounded test repairs; do not rewrite the
already-correct transport boundary or weaken logging, coverage or owner trust.
Use focused warning-strict tests and targeted transport coverage, binding the
unchanged named production spine and packaged dashboard receipts explicitly.
Complete isolated acceptance before marking done and merging one PR.

### Original implementation approach

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

- [x] Public GET and POST response disconnects close quietly without a second write.
- [x] A disconnect during the defensive 500 is also quiet and bounded.
- [x] Expected Windows and POSIX disconnect variants share one classifier across
  public HTTP and dashboard surfaces.
- [x] The affected observation is marked `degraded/client_disconnected` without
  logging private request content.
- [x] Genuine application failures still log and attempt exactly one sanitized 500.
- [x] Focused HTTP, dashboard-disconnect and runtime-observation tests, targeted
  transport coverage, and the named warning-strict production spine pass under
  ADR-0105.

## Requirement reconciliation

Only criterion 6 changes. Original wording: "Focused HTTP, dashboard-disconnect,
coverage, and warning-strict gates pass." The original implementation note below
treated this as pending current-head release coverage and the complete corpus.
ADR-0105 makes aggregate coverage, exhaustive corpus and interpreter matrix
optional owner-requested diagnostics, not completion requirements. The current
criterion keeps targeted coverage and warning-strict checks, with no aggregate
97-percent floor change or claim of an exhaustive pass. Criteria 1–5 are unchanged.

## Historical implementation evidence

Commit `12640d0` adds one shared classifier for built-in, POSIX-errno, and
Windows Winsock disconnect variants. Public GET/POST primary writes now close
quietly without logging or retrying. A guard inside each runtime boundary also
catches an abandoned defensive 500, marks the observation
`degraded/client_disconnected`, and stops; the outer request handler covers
parser and other pre-dispatch I/O. Dashboard handlers use the same classifier.
Unrelated OS errors still propagate, while genuine application failures log
once and attempt exactly one sanitized 500.

The public and dashboard disconnect suites pass 26 tests. The complete focused
HTTP/dashboard server package passes 154 tests with 3 skips in 75.41 seconds;
Ruff, format, and diff checks pass. Current-head coverage and warning-strict
release gates remain before closure. Tracker creation remains pending explicit
outward authorization.
