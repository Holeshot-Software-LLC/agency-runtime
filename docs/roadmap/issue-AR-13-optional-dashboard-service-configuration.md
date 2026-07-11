---
title: "AR-13: Add an optional cross-platform dashboard service and configuration parity"
status: done
category: roadmap
created: 2026-07-11
updated: 2026-07-11
tags: [dashboard, operations, configuration, installer]
related:
  - docs/decisions/0006-config-first-redacted-configuration.md
  - docs/decisions/0010-one-command-install-and-reversible-toggle.md
  - docs/decisions/0029-secure-local-dashboard-and-bounded-observability.md
  - docs/decisions/0031-optional-user-dashboard-service-and-shared-configuration.md
supersedes: []
superseded_by: null
type: issue
epic: operations
issue_id: AR-13
priority: p1
tracker_url: "https://github.com/Holeshot-Software-LLC/agency-runtime/issues/13"
depends_on: [AR-12]
blocks: [AR-07]
---

# AR-13: Add an optional cross-platform dashboard service and configuration parity

## Problem

The packaged dashboard runs as a foreground command. Installation does not
register a durable user-scoped service, offer an explicit service opt-out, or
let operators safely change configuration through the dashboard using the same
rules as the CLI.

## Current state

`agency install` now installs and starts an owned, user-scoped dashboard service
by default on supported Windows and Linux environments. Windows uses a limited
current-user Task Scheduler entry, Linux uses `systemd --user`, and
`agency install --no-dashboard` skips the component without affecting the rest
of installation. The lifecycle CLI provides dry-run planning plus idempotent
status, install, start, stop, restart, open, and uninstall operations; the
foreground `agency dashboard` command remains the explicit fallback when a user
service manager is unavailable.

The authenticated dashboard and CLI now share one typed, allowlisted
configuration transaction. Both validate the complete effective result before
an owner-private atomic replacement. Reads and mutation responses redact
secrets, environment overrides are reported without exposing their values, and
sensitive dashboard changes require exact in-page confirmation. The dashboard
port is configurable from either interface and service definition changes
restart only the owned dashboard service.

## Approach

Install and start a user-scoped dashboard service by default on supported
Windows and Linux environments, with `agency install --no-dashboard` as the
explicit opt-out. Use a per-user Task Scheduler entry on Windows and a
`systemd --user` unit on Linux. Make service planning and lifecycle operations
idempotent, reversible, and observable without requiring administrator access.
When a user service manager is unavailable, report that state truthfully and
preserve the foreground dashboard instead of claiming service installation.

Move configuration mutation behind one typed application service used by both
`agency config set` and the authenticated dashboard. Allowlist supported
settings, validate the resulting configuration before replacement, preserve
local-only policy, write atomically with restrictive permissions, redact
responses, and require exact confirmation for sensitive changes.

## Dependencies

Depends on `AR-12` for the packaged, authenticated dashboard. It coordinates
with the broader runtime-control work in `AR-04` and guided provider work in
`AR-05`, but their remaining acceptance criteria are not prerequisites for this
bounded service and configuration surface.

## Acceptance

- [x] Default installation registers and starts a user-scoped dashboard service on supported Windows and Linux environments.
- [x] `agency install --no-dashboard` leaves the dashboard service unregistered and unstarted while the remaining installation succeeds.
- [x] Service status, start, stop, restart, and uninstall operations are idempotent and reversible.
- [x] Service installation and lifecycle planning support a write-free dry run and never require system-wide installation.
- [x] The service preserves the dashboard's loopback-only authenticated security boundary.
- [x] The dashboard and CLI use the same typed service for supported configuration mutations.
- [x] Configuration reads remain redacted, and sensitive mutations require exact confirmation.
- [x] Configuration is fully validated before atomic replacement and retains restrictive permissions.
- [x] Windows and Linux contract tests exercise service plans without modifying the developer's real services.
- [x] Documentation distinguishes packaged assets, service registration, running state, foreground fallback, and installation opt-out.

## Verification

The final Windows regression suite passed with 532 tests and 2 platform skips.
Linux behavior was exercised through an isolated WSL source contract and a
built-wheel smoke test, including the `systemd --user` lifecycle plan,
owner-private configuration and runtime state, packaged dashboard assets, and
stale-revision rejection. Authenticated desktop and mobile-width browser checks
covered configuration rendering, mutation, confirmation, and responsive layout
without console errors. Ruff, high-severity Bandit, routing/delegation gates,
documentation validation, release hygiene, and wheel/sdist verification also
passed.

The local implementation is complete and is mapped to tracker issue
[#13](https://github.com/Holeshot-Software-LLC/agency-runtime/issues/13). The
issue remains open because closure was not part of the tracker-creation
authorization.
