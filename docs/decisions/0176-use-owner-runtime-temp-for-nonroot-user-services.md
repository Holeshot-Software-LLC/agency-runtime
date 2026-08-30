---
title: "Use owner-runtime temporary directories for non-root user services"
status: accepted
category: decisions
created: 2026-08-26
updated: 2026-08-26
tags: [dashboard, systemd, linux, security, temporary-files]
related:
  - docs/roadmap/issue-AR-301-private-systemd-dashboard-namespace.md
  - docs/roadmap/issue-AR-297-complete-unattended-container-bootstrap.md
  - docs/decisions/0031-optional-user-dashboard-service-and-shared-configuration.md
  - agency_runtime/core/dashboard_service_systemd.py
  - tests/test_dashboard_systemd_namespace_security.py
  - docs/worklog/README.md
supersedes: []
superseded_by: null
id: ADR-0176
type: decision
deciders: [maintainers]
---

# ADR-0176: Use owner-runtime temporary directories for non-root user services

## Context

The Linux dashboard is an ordinary systemd user service. On a non-root user
manager, enabling `PrivateTmp=true` implicitly enables a private user namespace.
That namespace omits the host-root mapping, so root-owned ancestors such as `/`
and `/home` appear with the overflow UID 65534 inside the worker. Agency's
configuration namespace validator then correctly refuses the exact owner-private
config because it cannot distinguish those remapped ancestors from paths
genuinely owned by UID 65534.

Accepting UID 65534 based only on an in-namespace ownership observation would
weaken the cross-account substitution boundary: mapped root and a genuinely
untrusted overflow owner are intentionally indistinguishable there. The service
still needs private temporary storage without depending on an operator-created
directory.

## Decision

For a non-root systemd user manager, and for WSL where the prior exception
already omitted `PrivateTmp`, install the dashboard unit with
`PrivateTmp=false`. Have systemd create `agency-runtime-dashboard` below the
owner's runtime directory with mode 0700 and bind `TMPDIR`, `TMP`, and `TEMP` to
that exact directory. Retain `UMask=0077`, `NoNewPrivileges=true`, the restricted
address-family set, loopback binding, and authenticated dashboard boundary.

A root user manager on non-WSL Linux retains `PrivateTmp=true`, because that
manager maps host root exactly and does not create the ambiguous ownership view.
Do not add a UID-remapping exception to configuration trust. A real path owned
by UID 65534 therefore remains rejected under the same validator used outside
systemd.

## Consequences

The ordinary non-root worker sees the real root-owned ancestor identities and
can validate its exact owner-private config. Temporary files created through
standard Linux environment discovery live in a systemd-managed owner-only
directory whose lifetime follows the unit. The generated unit is deterministic
for the manager identity and remains inspectable for drift.

`PrivateTmp` would also isolate a dependency that deliberately ignores all
three standard temporary-directory variables and hardcodes `/tmp`. Agency's
security-sensitive temporary paths use guarded private-directory creation and
do not rely on that behavior. Such a future dependency must be reviewed rather
than silently gaining an overflow-UID trust exception.

## Alternatives

Treating UID 65534 as remapped root was rejected because the service cannot
distinguish it from a genuine overflow owner. Reading another process's mount or
user namespace as an authority oracle was rejected because it is fragile,
privilege-dependent, and still does not bind every path component atomically.
Removing temporary-file hardening entirely was rejected because systemd can
provide an owner-scoped runtime directory directly. Converting the optional
dashboard to a privileged system service was rejected because it would broaden
authority and abandon the established user-service lifecycle.
