---
title: "Preserve configuration trust while adapting systemd hardening on WSL"
status: accepted
category: decisions
created: 2026-07-20
updated: 2026-07-20
tags: [dashboard, systemd, wsl, linux, security, portability]
related:
  - docs/roadmap/issue-AR-110-preserve-wsl-systemd-service-trust.md
  - docs/decisions/0031-optional-user-dashboard-service-and-shared-configuration.md
  - docs/roadmap/issue-AR-66-bind-systemd-unit-to-trusted-xdg-namespace.md
  - docs/THREAT_MODEL.md
  - docs/TROUBLESHOOTING.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
id: ADR-0075
type: decision
deciders: [maintainers]
---

# ADR-0075: Preserve configuration trust while adapting systemd hardening on WSL

## Context

The dashboard worker validates every configuration ancestor against
cross-account path substitution. Under WSL, a systemd user service with
`PrivateTmp=true` can observe root-owned ancestors through a mount namespace as
overflow UID `65534`. The same owner-private configuration is trusted outside
that namespace, but the distorted identity must still fail closed inside it.

The remaining user-unit controls do not cause the distortion:
`NoNewPrivileges=true`, `UMask=0077`, restricted address families, loopback-only
dashboard binding, and owner-private configuration, store, and runtime paths all
remain compatible.

## Decision

Do not weaken or special-case the shared configuration namespace predicate.
Instead, identify WSL only from bounded kernel-release evidence while generating
the systemd user unit and omit `PrivateTmp` only on a positive match. Retain
`PrivateTmp=true` on normal Linux and whenever the evidence is absent, malformed,
oversized, unreadable, or otherwise unknown.

Retain every other dashboard service hardening control on WSL. Treat a generated
unit, registration, and active process as lifecycle evidence only; readiness and
health must still prove that the installed worker can read the trusted
configuration and serve the authenticated local endpoint.

## Consequences

- WSL systemd no longer creates a false cross-account identity for trusted
  configuration ancestors.
- Normal Linux preserves private temporary-directory isolation.
- Unknown environments take the secure normal-Linux path.
- WSL processes share the host temporary namespace, but Agency does not place
  configuration, credentials, its SQLite store, or dashboard bearer material in
  that namespace; their owner-private path controls remain mandatory.
- Real WSL service readiness becomes a release gate for this exception.

## Alternatives

- **Accept overflow UID ancestors in the namespace predicate.** Rejected because
  it would weaken a shared security boundary for configuration and policy reads.
- **Disable `PrivateTmp` on every Linux host.** Rejected because the
  incompatibility is WSL-specific and normal Linux benefits from the isolation.
- **Use WSL environment variables.** Rejected because service-manager
  environments can differ from installer environments and are not kernel
  evidence.
- **Leave WSL service mode unsupported.** Rejected because the user service and
  worker are otherwise functional and the narrow adaptation preserves the
  stronger path-identity control.
