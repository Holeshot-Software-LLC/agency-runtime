---
title: "AR-74: Broker restricted Windows host controls through the dashboard"
status: done
category: roadmap
created: 2026-07-16
updated: 2026-07-17
tags: [operations, cli, dashboard, windows, security, portability]
related:
  - docs/decisions/0031-optional-user-dashboard-service-and-shared-configuration.md
  - docs/decisions/0053-durable-fail-enabled-master-control.md
  - docs/decisions/0058-broker-restricted-windows-host-controls.md
  - docs/THREAT_MODEL.md
  - docs/TROUBLESHOOTING.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: operations
issue_id: AR-74
priority: p0
tracker_url: "https://github.com/Holeshot-Software-LLC/agency-runtime/issues/75"
depends_on: [AR-57, AR-70]
blocks: [AR-75, AR-77]
---

# AR-74: Broker restricted Windows host controls through the dashboard

## Problem

From a restricted Codex process, `agency status --json` and host-scoped
`agency on|off` construct the SQLite Store directly. If the default Store
namespace needs an owner-only ACL repair, Windows correctly rejects that
mutation under the restricted token, but the CLI raises a traceback instead of
using the already authenticated user dashboard service as its least-privilege
broker.

## Current state

The implementation now uses the authenticated loopback service only after an
exact restricted-token Store refusal, with direct normal-shell and native
lifecycle paths preserved. Host snapshots and toggle receipts include the
service's config and Store identity. Full-suite and installed restricted-Codex
acceptance remain pending.

## Approach

Keep direct Store access as the primary path. When and only when Store
construction is refused because the Windows token is restricted, read host
status or apply host-control compare-and-swap mutations through the
owner-private dashboard descriptor and authenticated loopback API. Validate the
bounded response shape, exact host identity, booleans, and non-negative
generations. Bind the response to the canonical default config path/revision,
active and desired Store paths, environment overrides, and false
restart-required state; serialize mutations against config writers. If the
service is absent, stale, drifted, or invalid, return a sanitized nonzero CLI
result without a traceback. Preserve dry-run, multi-host, and native-lifecycle
behavior.

## Dependencies

AR-57 defines the existing restricted-process master-control broker. AR-70
defines generation-checked host mutations. ADR-0058 constrains this fallback to
the exact restricted-token boundary and the authenticated local service.

## Acceptance

- [x] Restricted `agency status` brokers host status through the authenticated dashboard.
- [x] Restricted host-scoped `agency on|off` brokers CAS mutations and dry runs without a local Store.
- [x] Normal user shells retain direct Store access and native lifecycle remains independent.
- [x] Missing, unauthenticated, stale, malformed, or mismatched broker responses fail closed without a traceback.
- [x] Broker payloads are bounded and validate exact host identity, booleans, and generations.
- [x] Windows-simulated tests and an installed restricted-Codex smoke pass.
- [x] Exact coverage, full-suite, tracker, and merged-install gates pass.
