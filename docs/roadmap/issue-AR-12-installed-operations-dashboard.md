---
title: "AR-12: Ship a secure installed operations dashboard"
status: done
category: roadmap
created: 2026-07-10
updated: 2026-07-18
tags: [dashboard, operations, security]
related:
  - docs/decisions/0010-one-command-install-and-reversible-toggle.md
  - docs/decisions/0012-canonical-sqlite-audit-store.md
  - docs/decisions/0017-sanitized-server-error-boundary.md
  - docs/decisions/0027-authoritative-runtime-evidence-traces.md
  - docs/decisions/0029-secure-local-dashboard-and-bounded-observability.md
supersedes: []
superseded_by: null
type: issue
epic: operations
issue_id: AR-12
priority: p1
tracker_url: "https://github.com/Holeshot-Software-LLC/agency-runtime/issues/12"
depends_on: [AR-10]
blocks: [AR-07, AR-13, AR-14, AR-89, AR-94]
---

# AR-12: Ship a secure installed operations dashboard

## Problem

Operators need one installed interface to understand routing, delegation,
provider and host health, roster state, retention, and configuration without
assembling CLI output. Exposing those controls through the current unauthenticated
HTTP service would create an unsafe local attack surface.

## Current state

The package now includes a dark local operations dashboard, route/explain lab,
recent routing and evidence tables, roster/snapshot views, host maturity cards,
redacted configuration, native host/roster controls, and retention maintenance.
It binds only to loopback, uses a per-launch bearer token, validates `Host` and
origin, rejects non-JSON mutations, validates destructive ranges and booleans,
and requires exact confirmation phrases.

Content capture is disabled by default; opt-in callback capture is bounded and
redacted. Runtime retention defaults to 30 days. The dashboard presents an
authoritative delegation dependency graph, receipt-based provider health,
explicit unknown and stale states, bounded parallel host inspection, and
responsive desktop/mobile rendering.

Native-Windows tests and a real browser session verified authenticated and
unauthenticated flows, route/evidence refresh, long-path rendering, and
responsive layout without console errors. An isolated Ubuntu/WSL wheel install
served the packaged dashboard assets, rejected unauthenticated API access,
accepted the per-launch token, passed all seven generated-host smoke checks and
the v1.1 routing evaluation, and passed dependency validation.

## Approach

Install a dense, dark, system-theme-aware local operations cockpit served by
the Python package. Bind to loopback, use a per-launch token and origin/CSRF
checks, default to metadata-only observability with opt-in redacted content,
and retain runtime data for 30 days by default. Require explicit confirmation
for mutations and reuse the same typed application services as the CLI.

## Dependencies

Depends on `AR-10` so displayed evidence and controls operate on trustworthy
state. Host-specific controls also inherit the verification requirements in
`AR-03` and `AR-04`.

## Acceptance

- [x] `agency dashboard` starts and opens a loopback-only authenticated UI.
- [x] The dashboard shows routing decisions, evidence, delegation graphs, host and provider health, and roster state.
- [x] Route/explain testing and safe operational controls use shared application services.
- [x] Mutations require explicit confirmation and CSRF-safe authenticated requests.
- [x] Raw prompts and outputs are disabled by default; redacted capture is opt-in.
- [x] Runtime retention defaults to 30 days and is operator-configurable.
- [x] Installation and dashboard tests pass on native Windows and Ubuntu/WSL.
