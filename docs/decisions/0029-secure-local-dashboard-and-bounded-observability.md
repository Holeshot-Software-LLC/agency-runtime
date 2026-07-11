---
title: "Keep the operations dashboard local and observability bounded"
status: accepted
category: decisions
created: 2026-07-10
updated: 2026-07-11
tags: [dashboard, security, privacy, retention]
related:
  - docs/roadmap/issue-AR-12-installed-operations-dashboard.md
  - docs/roadmap/issue-AR-07-public-release-readiness.md
  - docs/roadmap/issue-AR-13-optional-dashboard-service-configuration.md
  - docs/roadmap/issue-AR-14-live-signal-observatory.md
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
