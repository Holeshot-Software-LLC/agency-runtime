---
title: "AR-170: Fail dashboard response correlation closed"
status: in_progress
category: roadmap
created: 2026-07-27
updated: 2026-07-27
tags: [dashboard, ui, traceability, accessibility, security]
related:
  - docs/decisions/0027-authoritative-runtime-evidence-traces.md
  - docs/decisions/0029-secure-local-dashboard-and-bounded-observability.md
  - docs/decisions/0095-complete-paginated-dashboard-collections.md
  - docs/decisions/0096-require-operator-presence-for-persistent-controls.md
  - docs/roadmap/issue-AR-138-coherent-observable-dashboard-ui.md
  - docs/roadmap/issue-AR-153-complete-worker-detail-evidence.md
  - docs/roadmap/issue-AR-166-truthful-dashboard-disclosure-and-correlation.md
  - docs/roadmap/issue-AR-175-retire-dashboard-control-fallback.md
  - agency_runtime/dashboard/app.css
  - agency_runtime/dashboard/app.js
  - agency_runtime/dashboard/dashboard-actions.js
  - agency_runtime/dashboard/dashboard-config.js
  - agency_runtime/dashboard/dashboard-core.js
  - agency_runtime/dashboard/dashboard-live.js
  - agency_runtime/dashboard/index.html
  - tests/dashboard_ui.test.mjs
supersedes: []
superseded_by: null
type: issue
epic: dashboard
issue_id: AR-170
priority: p1
tracker_url: null
depends_on: [AR-138, AR-153, AR-166]
blocks: [AR-175]
---

# AR-170: Fail dashboard response correlation closed

## Problem

The dashboard accepted worker-detail and exact-roster responses without proving
that the returned identity matched the requested worker or slug. A late,
stale, malformed, or incorrectly routed response could therefore render
authoritative-looking evidence for the wrong governed worker.

The shared browser request helper also let caller-supplied header objects
override `Authorization` and request identity, and it accepted any syntactically
valid response UUID rather than requiring the exact UUID it sent. Present but
malformed identifiers disappeared into the same fallback as an absent legacy
header. These paths were not used by shipped callers and did not bypass server
authentication, but they made the client boundary fail open to future call-site
mistakes and could misattribute debugging evidence.

The live UI audit also found lower-severity truth and accessibility defects. An
author stylesheet overrode the native `hidden` contract and exposed inert
lifecycle controls, asynchronous configuration rendering changed the visible
read-only status to `No unsaved changes`, token-fragment cleanup broke the skip
link, the overview title clipped at the audited desktop viewport, and settings
presented dashboard retention controls that could never dispatch.

## Current state

Worker detail is committed only after exact canonical slug, non-empty worker
identity, nonnegative safe-integer revision, and all four required evidence
collections validate.
Exact roster lookup proves the requested `filter_slug`, accepts at most one row,
and requires every returned row to carry the same exact primitive slug; case or
whitespace canonicalization is never applied to a server response. The current
control path captures the request path and identity once and validates before
changing last-good state. AR-175 removes the unsupported legacy fallback.

The request helper normalizes caller headers through the browser `Headers`
contract, then overwrites every protected authorization, current/legacy request
identity, and JSON content-type field. Every present response identity must be
a canonical UUID string exactly equal to the sent UUID. Missing legacy identity
can use the sent value; present-invalid or mismatched identity rejects the
response and never reflects hostile text.

The monitoring surface now has a global `hidden` invariant, durable read-only
state, native non-token fragment navigation, wrapping headings, and truthful
attended-maintenance copy with the unreachable retention form removed.

## Approach

Validate response identity at the browser boundary before rendering or state
commit, while retaining abort/generation checks for request ordering. Keep the
dashboard read-only contract in state as well as disabled controls. Treat
token fragments as authentication material but preserve ordinary in-page
fragments. Remove inert persistent-control markup instead of presenting a
control that the server will never accept.

## Dependencies

ADR-0027 requires authoritative correlated evidence. ADR-0029 and ADR-0096
bound the dashboard to authenticated local monitoring without persistent
control authority. ADR-0095 requires complete, versioned collection truth.

Tracker creation remains pending explicit outward-write authorization.

## Acceptance

- [x] Worker-detail responses must match the exact requested governed worker.
- [x] Worker detail requires a safe revision and all four evidence arrays;
  missing evidence cannot be rendered as truthful emptiness.
- [x] Exact-roster responses must match the exact requested slug on every
  current control and paginated collection path.
- [x] Caller headers cannot override bearer or request identity, and every
  present response UUID is canonical and equals the sent request UUID.
- [x] Invalid or stale responses retain last-good state and expose a correlated
  failure instead of rendering mismatched evidence.
- [x] Hidden controls stay hidden and read-only status survives asynchronous
  configuration rendering.
- [x] Skip-link navigation, heading layout, and attended-maintenance copy are
  truthful at the audited desktop and keyboard surfaces.
- [x] The focused browser suite and live seven-view/six-tab interaction sweep
  pass without application console errors.
- [ ] The final repository release gate passes at the implementation commit.

## Implementation evidence

The dashboard specialist audited 131 source-defined interactive and form
elements, seven navigation views, six evidence tabs, all event listeners, and
every reachable fetch path. The current source passed 105 Node interaction
tests and a live repo-source browser sweep of all seven views and all six tabs.
No duplicate IDs, broken `aria-controls`, enabled mutation controls, or
application console errors remained. Aggregate release evidence is recorded
only after the final integrated gate.
