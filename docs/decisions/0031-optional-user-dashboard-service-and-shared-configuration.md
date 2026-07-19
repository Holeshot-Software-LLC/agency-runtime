---
title: "Use an optional user-scoped dashboard service with one typed configuration boundary"
status: accepted
category: decisions
created: 2026-07-11
updated: 2026-07-16
tags: [dashboard, operations, configuration, installer, security]
related:
  - docs/roadmap/issue-AR-13-optional-dashboard-service-configuration.md
  - docs/roadmap/issue-AR-14-live-signal-observatory.md
  - docs/roadmap/issue-AR-66-bind-systemd-unit-to-trusted-xdg-namespace.md
  - docs/roadmap/issue-AR-71-dashboard-accessible-truthful-states.md
  - docs/roadmap/issue-AR-74-broker-restricted-windows-host-controls.md
  - SECURITY.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
id: ADR-0031
type: decision
deciders: []
---

# ADR-0031: Use an optional user-scoped dashboard service with one typed configuration boundary

## Context

The installed dashboard is useful only while an operator keeps its foreground
process running. Starting it automatically improves availability, but a
system-wide daemon would require unnecessary authority, and silently adding any
background process without an opt-out would violate least-change expectations.
Windows and Linux also expose different user-service mechanisms.

The dashboard currently reads redacted configuration while CLI mutation follows
its own write path. Separate writers can disagree about typing, validation,
local-only policy, permissions, and redaction. Giving a browser a generic YAML
write endpoint would enlarge the local control plane and make secrets easier to
expose.

## Decision

Treat background dashboard execution as an optional, user-scoped installation
component. A normal `agency install` registers and starts it by default;
`agency install --no-dashboard` skips registration and startup without
preventing the remaining installation. The opt-out controls the background
service, not whether package-owned dashboard assets exist.

Use a per-user Task Scheduler entry on Windows and a `systemd --user` unit on
Linux. Do not require administrator privileges, write a system service, or
restart unrelated processes. Provide idempotent status, start, stop, restart,
and uninstall operations plus write-free planning. If the native user-service
manager is unavailable, report an explicit unsupported state and leave
`agency dashboard` available as the foreground fallback.

Honor an absolute `XDG_CONFIG_HOME` only when its real ancestor chain prevents
cross-account path substitution. Bind unit writes, reads, rollback, and removal
to that trusted namespace; an unsafe or changing XDG path fails closed without
falling back to a different registration location.

Treat the systemd user manager environment as a second service-start input, not
as equivalent to the installer process environment. If its bounded
`show-environment` output contains a supported runtime override or configured
credential variable, block planning and mutation with a names-only diagnostic;
never copy or return the value.

Run the service through the same package entry point and preserve ADR-0029's
loopback binding, process-scoped bearer authentication, origin checks, bounded
observability, and redacted output. Service registration or running state is
not evidence that a browser has authenticated successfully.

Put supported configuration mutation behind one typed application service.
Both `agency config set` and dashboard endpoints must load the current user
configuration, parse an allowlisted setting into its declared type, enforce
profile policy, validate the complete result, and atomically replace the file
with restrictive permissions. Normal responses never return credential values.
The dashboard additionally requires its authenticated mutation boundary and an
exact confirmation phrase for sensitive changes. Arbitrary YAML replacement is
not a dashboard operation.

## Consequences

- Windows and Linux users receive a durable dashboard without granting
  system-wide installation authority.
- Operators can opt out before any dashboard service state is created and can
  remove that state later through a defined lifecycle command.
- Linux environments without a working user service manager retain a truthful
  foreground fallback instead of a false successful-service claim.
- CLI and dashboard behavior cannot drift into separate validation, profile,
  permission, or redaction rules.
- New editable settings require an explicit typed schema addition rather than
  becoming writable automatically.
- The existing local dashboard threat model remains in force even when the
  process starts automatically.

## Alternatives

- Require operators to start the dashboard manually. Rejected because an
  installed operations surface should be available without keeping a terminal
  open.
- Install a system-wide Windows service or Linux unit. Rejected because the
  local single-user dashboard does not justify administrator authority.
- Make service installation separately opt-in. Rejected because the requested
  install experience includes the dashboard by default and provides an
  explicit opt-out.
- Let the dashboard edit raw YAML. Rejected because it bypasses typed
  validation, increases secret-exposure risk, and can diverge from CLI policy.
- Maintain independent dashboard and CLI writers. Rejected because duplicated
  mutation rules will drift.

## Provenance

`AR-13` records the implementation and verification work for this decision.
The implementation commit will be linked through the roadmap and worklog after
it exists.
