---
title: "Use adaptive authenticated polling and source-owned signal visualizations"
status: accepted
category: decisions
created: 2026-07-11
updated: 2026-07-11
tags: [dashboard, live-updates, visualization, security, accessibility]
related:
  - docs/roadmap/issue-AR-175-retire-dashboard-control-fallback.md
  - docs/roadmap/issue-AR-14-live-signal-observatory.md
  - docs/decisions/0029-secure-local-dashboard-and-bounded-observability.md
  - docs/decisions/0031-optional-user-dashboard-service-and-shared-configuration.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
id: ADR-0032
type: decision
deciders: []
---

# ADR-0032: Use adaptive authenticated polling and source-owned signal visualizations

## Context

The dashboard must feel live while preserving the local security boundary in
ADR-0029. Native EventSource cannot attach the existing bearer authorization
header; placing that token in a query string would expose it to request logs.
A long-lived fetch stream would occupy one server thread per tab and still need
to poll SQLite because runtime writes happen across processes.

The dashboard is installed directly from a Python wheel and intentionally has
no frontend build pipeline. Adding React only to consume branded component or
chart libraries would enlarge artifacts, create a second dependency supply
chain, and weaken offline packaging without improving the underlying evidence.

## Decision

Expose one authenticated metadata-only GET endpoint for live dashboard state.
It reads bounded recent activity once, derives overview summaries from that
snapshot, includes cheap database sizes, and returns a stable revision that
changes only when observable content changes. It never includes configuration
secrets or puts authorization material in URLs.

Use recursive single-flight fetch polling rather than EventSource, WebSocket,
or setInterval. Poll quickly only while visible, abort on page hide, refresh
immediately on visibility or back-forward-cache recovery, add capped
exponential backoff
with jitter for transient errors, and stop on authentication or authorization
failure. Discard stale generations and never retry mutations automatically.

Keep host discovery, roster snapshots, and configuration out of the fast path.
Live snapshots update only runtime evidence. A slower control-plane tier keeps
those surfaces current, while full refreshes are limited to initial load,
explicit refresh, and mutation reconciliation. Neither tier may replace a
dirty configuration form.

Build controls, motion, and charts from semantic HTML, CSS, and small
source-owned JavaScript modules. Charts use bounded data, accessible summaries,
and CSP-compatible geometry. Motion is limited to opacity and transforms,
pauses offscreen, and honors reduced-motion and forced-colors preferences.
Metrics must describe bounded observed data honestly; decorative or invented
telemetry is prohibited.

## Consequences

- Operators see current routing and delegation evidence without manual refresh.
- Bearer authentication, same-origin enforcement, CSP, and offline packaging
  remain unchanged.
- The fast loop performs one bounded activity read instead of repeatedly
  rebuilding six dashboard surfaces or invoking native host inspection.
- Visual components remain auditable in the wheel and add no runtime network or
  package dependency.
- Source-owned charts and controls require focused accessibility and rendering
  tests because a third-party component contract is not available.
- A restarted service rotates its token; the client stops and tells the operator
  to reopen the dashboard instead of retrying forever.

## Alternatives

- Use EventSource. Rejected because it cannot send the current authorization
  header and a token-bearing URL is unacceptable.
- Use WebSocket or streaming fetch. Rejected because the threaded local server
  has no event bus and would still poll SQLite while holding a connection.
- Refresh the whole dashboard on an interval. Rejected because it duplicates
  queries, invokes expensive host discovery, rebuilds hidden DOM, and can erase
  unsaved configuration edits.
- Add React, shadcn, and Ant Charts. Rejected because the installed dashboard
  does not otherwise need a frontend runtime or build pipeline; their design
  quality is reproduced through smaller semantic source-owned primitives.
- Load controls or charts from a CDN. Rejected because the dashboard must be
  offline, self-contained, and compatible with its strict CSP.

## Provenance

AR-14 records implementation and verification. Its implementation commit will
be linked through the roadmap and worklog after it exists.
