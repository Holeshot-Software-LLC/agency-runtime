---
title: "AR-75: Broker restricted Windows agent controls through the dashboard"
status: done
category: roadmap
created: 2026-07-16
updated: 2026-07-17
tags: [roster-governance, cli, dashboard, windows, security, portability]
related:
  - docs/decisions/0046-config-backed-agent-activation-policy.md
  - docs/decisions/0058-broker-restricted-windows-host-controls.md
  - docs/decisions/0059-broker-restricted-windows-agent-controls.md
  - docs/THREAT_MODEL.md
  - docs/TROUBLESHOOTING.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: roster-governance
issue_id: AR-75
priority: p0
tracker_url: "https://github.com/Holeshot-Software-LLC/agency-runtime/issues/76"
depends_on: [AR-28, AR-74]
blocks: [AR-76]
---

# AR-75: Broker restricted Windows agent controls through the dashboard

## Problem

From a restricted Codex process, `agency agents list`, `agency agents enable`,
and `agency agents disable` open the SQLite Store directly. If the owner-only
Store namespace needs an ACL repair, Windows correctly refuses that mutation
under the restricted token, but the CLI can raise before returning agent state
or applying the reversible configuration policy. This breaks the required
CLI/dashboard parity for per-agent controls.

## Current state

The implementation now brokers compact activation pages, one exact-agent
lookup, and one revision-checked toggle after an exact restricted-token refusal.
Responses carry config, Store, and roster identity, while full selector metadata
is absent from bulk pages. Full-suite and installed restricted-Codex acceptance
remain pending.

## Approach

Keep direct config and Store access for normal shells. When and only when the
exact restricted-Windows-token refusal occurs on the default installed identity,
use narrow authenticated dashboard endpoints for compact paginated activation
state, exact-slug lookup, and one revision-checked agent toggle. Bind those
responses to the service config path/revision, active and desired Store paths,
restart-required state, and roster revision. Validate bounded pagination,
canonical unique slugs, protected/enabled booleans, exact identity continuity,
and toggle receipt coherence. Repeat Store binding, roster membership,
confirmation, and disabled-set preconditions inside the config writer lock.
Do not proxy arbitrary configuration or explicit `--config` identities, and
do not retry a stale revision.

## Dependencies

AR-28 defines reversible activation and protected coordinators. AR-74 defines
the exact restricted-token dashboard-broker boundary. ADR-0059 limits this
extension to narrow agent-control operations rather than a generic Store or
configuration proxy.

## Acceptance

- [x] Restricted `agency agents list` returns the complete paginated governed roster.
- [x] Restricted `agency agents enable|disable` uses exact lookup, confirmation, and one revision CAS.
- [x] Normal shells retain direct access and explicit `--config` is never redirected.
- [x] Protected coordinators remain immutable on every path.
- [x] Compact broker pages validate config/Store/roster identity continuity, canonical unique slugs, booleans, bounds, and counts.
- [x] Bulk list brokerage excludes full selector metadata; exact lookup returns at most one canonical agent.
- [x] Missing, unauthenticated, stale, malformed, duplicate, oversized, or mismatched evidence fails closed.
- [x] Windows-simulated tests and an installed restricted-Codex smoke pass.
- [x] Exact coverage, full-suite, tracker, and merged-install gates pass.
