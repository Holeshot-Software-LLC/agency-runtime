---
title: "AR-166: Keep dashboard disclosure and correlation truthful"
status: in_progress
category: roadmap
created: 2026-07-27
updated: 2026-07-27
tags: [dashboard, security, privacy, observability, ui]
related:
  - docs/decisions/0027-authoritative-runtime-evidence-traces.md
  - docs/decisions/0029-secure-local-dashboard-and-bounded-observability.md
  - docs/decisions/0096-require-operator-presence-for-persistent-controls.md
  - docs/roadmap/issue-AR-138-coherent-observable-dashboard-ui.md
  - docs/roadmap/issue-AR-149-fresh-dashboard-request-ids.md
  - docs/roadmap/issue-AR-153-complete-worker-detail-evidence.md
  - agency_runtime/dashboard/app.js
  - agency_runtime/dashboard/dashboard-actions.js
  - agency_runtime/dashboard/dashboard-config.js
  - agency_runtime/dashboard/dashboard-core.js
  - agency_runtime/dashboard/dashboard-live.js
  - agency_runtime/dashboard/dashboard-render.js
  - tests/dashboard_ui.test.mjs
supersedes: []
superseded_by: null
type: issue
epic: dashboard
issue_id: AR-166
priority: p2
tracker_url: null
depends_on: []
blocks: [AR-170, AR-171, AR-173]
---

# AR-166: Keep dashboard disclosure and correlation truthful

## Problem

Three low-severity presentation gaps remained after the production dashboard
trace. Provider-option rendering could re-enable one selector after the settings
form became read-only. Failed requests retained a safe request ID internally but
most user-visible notices omitted it, and a successful Route Lab receipt did not
show it. Finally, the global `Metadata only` chip did not say that it described
runtime observation capture while owner-only worker detail can display a bounded
compiled governed specialist definition.

None of these gaps bypassed dashboard authentication or mutation denial. They
could nevertheless mislead an operator about available authority, complicate
support correlation, or make the privacy boundary appear broader than it is.

## Current state

Provider-secret options remain visible for inspection but the selector stays
disabled after every render. Client request IDs are canonical UUIDv4 values;
HTTP and transport failures append only a validated identifier to their inert
text notice, and hostile response identifiers fall back to the browser's safe
request identity. Successful Route Lab receipts show the validated request ID.

The privacy chip now says `Runtime metadata only` or
`Redacted runtime content`, matching the `observability.capture_content`
runtime-observation setting. Owner-only worker detail retains its existing
8,192-character compiled prompt bound and labels that preview as a governed
specialist definition separate from runtime observation capture. This does not
broaden broker scope, retention, or content-capture authority.

## Approach

Centralize bounded request-ID validation and notice formatting in the dashboard
core, then reuse it for API errors and fixed terminal notices. Render a Route Lab
request ID only after the same validation. Preserve the read-only invariant in
the provider-option renderer itself rather than relying on initialization order.
Make runtime-capture wording explicit both during bootstrap and after config or
overview refresh, and disclose the owner-only compiled-definition distinction at
the preview.

## Dependencies

ADR-0027 requires request-level traceability. ADR-0029 governs local dashboard
privacy and runtime observation capture. ADR-0096 makes every persistent
dashboard control read-only. AR-138, AR-149, and AR-153 own the broader coherent
UI, request identity, and bounded worker-detail contracts respectively.

Tracker creation remains pending owner authorization; no outward tracker write
was performed in this local implementation slice.

## Acceptance

- Provider rendering cannot re-enable the provider-secret selector or any other
  persistent dashboard control.
- HTTP, transport, authentication, and reconciliation failures expose a safe
  request ID when one exists without reflecting an invalid identifier.
- Successful Route Lab receipts display their validated request ID; malformed
  identifiers remain absent from rendered evidence.
- The privacy chip explicitly describes runtime observation capture.
- The bounded owner-only compiled specialist definition is labeled separately
  from runtime capture without changing authentication or broker scope.
- Focused dashboard UI, documentation, formatting, and diff checks pass.

## Implementation evidence

The complete dashboard UI suite passes 102 tests, including provider re-render,
hostile request-ID fallback, terminal authentication notice, successful Route
Lab receipt, runtime-capture wording, and owner-preview disclosure regressions.
Ruff check and format validation pass across 577 files. Metadata validation and
documentation verification pass across 424 Markdown files, the policy and
worklog generated-state checks pass, and `git diff --check` passes.
Installed-browser and full release validation are not claimed by this bounded
slice.
