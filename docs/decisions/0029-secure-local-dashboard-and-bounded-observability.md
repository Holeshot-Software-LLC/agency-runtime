---
title: "Keep the operations dashboard local and observability bounded"
status: accepted
category: decisions
created: 2026-07-10
updated: 2026-07-18
tags: [dashboard, security, privacy, retention]
related:
  - docs/roadmap/issue-AR-54-make-dashboard-runtime-publication-swap-safe.md
  - docs/roadmap/issue-AR-42-make-database-metrics-sidecar-race-safe.md
  - docs/roadmap/issue-AR-12-installed-operations-dashboard.md
  - docs/roadmap/issue-AR-07-public-release-readiness.md
  - docs/roadmap/issue-AR-13-optional-dashboard-service-configuration.md
  - docs/roadmap/issue-AR-14-live-signal-observatory.md
  - docs/roadmap/issue-AR-15-reliable-json-rejection-responses.md
  - docs/roadmap/issue-AR-17-production-hardening-portability.md
  - docs/roadmap/issue-AR-19-bounded-overload-responses.md
  - docs/roadmap/issue-AR-28-reversible-agent-activation-controls.md
  - docs/roadmap/issue-AR-32-windows-dashboard-task-xml-canonicalization.md
  - docs/roadmap/issue-AR-38-dashboard-service-environment-durability.md
  - docs/roadmap/issue-AR-40-dashboard-config-identity-binding.md
  - docs/roadmap/issue-AR-71-dashboard-accessible-truthful-states.md
  - docs/roadmap/issue-AR-96-packaged-dashboard-favicon.md
  - SECURITY.md
  - docs/RELEASE_CHECKLIST.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
id: ADR-0029
type: decision
deciders: []
---

# ADR-0029: Keep the operations dashboard local and observability bounded

## Context

Operators need one view of routing decisions, evidence, roster state, host
maturity, configuration, and retention. Those controls can mutate local native
host state and SQLite governance data. An unauthenticated server, permissive
binding, cross-origin browser access, or raw-prompt default would turn a local
diagnostic tool into a material security and privacy risk.

## Decision

Ship the dashboard as package-owned static assets served by the Python runtime.
Bind only to loopback and reject any non-loopback server configuration. Generate
a high-entropy bearer token for each dashboard process, deliver it in the URL
fragment, remove the fragment after session-storage capture, and require the
token for every API request.

Validate the loopback `Host`, reject cross-origin requests and preflight, accept
mutation bodies only as JSON, bound request size, send no-store and restrictive
browser security headers, and sanitize internal errors. Require exact,
operation-specific confirmation phrases for roster activation, host toggles,
and destructive retention.

Default to metadata-only evidence with `capture_content: false`. If an operator
opts in, keep captured content bounded and defensively redact common credentials
and personal identifiers. Document that redaction is not complete data-loss
prevention. Set runtime retention to 30 days by default and apply it when the
dashboard starts; preserve roster-governance tables.

The dashboard displays native maturity as reported by the installer. It may not
promote cold inventory into loaded/canary truth.

On Windows, register the background dashboard from BOM-bearing UTF-16 task XML.
Bind its principal and trigger to identities resolved from the current process
token, inspect canonical task XML through bounded Base64-encoded UTF-8 COM
output, and accept only the documented schema/default normalization. Ownership
markers permit repair or removal but never execution: start and restart also
require semantic definition equality plus an exact pre-mutation requery.

## Consequences

- The installed package provides an operations UI without Node.js or a remote
  service.
- An active local token is powerful and must not be logged, shared, or exposed
  through a proxy.
- Restarting the dashboard invalidates old tabs and tokens.
- Operators must make an explicit data-governance choice before prompt content
  is retained.
- Automatic runtime trimming bounds common local growth, while manual CLI trim
  remains available.
- This design is not a remote multi-user dashboard; remote access would require
  a separate threat model and decision.
- Windows service repair remains available for an owned drifted task, but
  start/restart fail closed until repair restores the canonical definition.

## Alternatives

- Reuse the unauthenticated HTTP API as the UI backend. Rejected because browser
  and local-process threats require a separate authenticated boundary.
- Bind to all interfaces for convenience. Rejected because bearer-token-only
  local authority is not sufficient for network exposure.
- Store full prompts and outputs by default. Rejected because most operational
  views need metadata, not content.
- Never trim automatically. Rejected for the installed dashboard because the
  agreed default is bounded 30-day runtime history.

## Provenance

The production-readiness refactor added the package-owned dashboard, loopback
and token boundary, origin/host/content-type checks, explicit mutation
confirmations, metadata-only defaults, opt-in redaction, and configurable
30-day runtime retention. The implementation commit is recorded through the
worklog after it is created.
