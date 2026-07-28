---
title: "AR-196: Authorize prepared dashboard-service install and repair"
status: in_progress
category: roadmap
created: 2026-07-28
updated: 2026-07-28
tags: [windows, dashboard, service, security, operator-presence]
related:
  - docs/decisions/0031-optional-user-dashboard-service-and-shared-configuration.md
  - docs/decisions/0051-bind-dashboard-runtime-publication-to-validated-filesystem-identities.md
  - docs/decisions/0096-require-operator-presence-for-persistent-controls.md
  - docs/decisions/0109-prepare-dashboard-service-repair-before-operator-presence.md
  - docs/roadmap/issue-AR-143-require-operator-presence-for-controls.md
  - docs/roadmap/issue-AR-161-sign-and-license-windows-operator-presence-delivery.md
  - docs/roadmap/issue-AR-194-inspect-owned-service-runtimes-across-python-versions.md
  - agency_runtime/core/operator_presence.py
  - agency_runtime/core/windows_operator_presence.py
  - agency_runtime/core/dashboard_service_install.py
  - agency_runtime/core/dashboard_service_core.py
  - agency_runtime/cli/service_commands.py
  - agency_runtime/native/windows/operator_presence/operator_presence_verifier.cpp
  - tests/test_cli_operator_presence.py
  - tests/test_dashboard_service.py
  - tests/test_windows_operator_presence.py
supersedes: []
superseded_by: null
type: issue
epic: security
issue_id: AR-196
priority: p0
tracker_url: null
depends_on: [AR-143, AR-161]
blocks: [AR-194]
---

# AR-196: Authorize prepared dashboard-service install and repair

## Problem

Every persistent dashboard-service command reaches the generic
operator-presence boundary, whose OS verifier is intentionally unavailable.
The commands therefore fail closed before their handlers run. This is secure,
but it makes an owned stale service impossible to install or repair through the
documented attended CLI path. `dashboard service open` is also classified as a
mutation because it may auto-repair, so even a healthy read/open path is gated.

## Current state

Exact installed revision `10ce6e0` can now inspect the Python-3.13-owned
service from the Python-3.10 CLI and truthfully reports it installed, enabled,
inactive, unreachable, stale, and repair-recommended. Running the documented
repair command returns `unavailable: a non-exporting OS operator-presence
verifier is not available` and dispatches no mutation. Existing Windows Hello
support is action-specific to roster rollback, existing Codex refresh, and
owned host uninstall; its result cannot safely authorize adjacent service
state. Tracker creation remains pending explicit authorization.

## Approach

Add one exact Windows 11 x64 prepared action for idempotent dashboard-service
install-or-repair. Build a write-free immutable plan that binds the owner,
configuration, manifest, task definition, runtime, Python/launcher identities,
desired transition, and private publication plan. Show the human a bounded
current-to-target consequence, invoke the pinned non-exporting verifier, then
take the service lock and fully reprepare before any write. Reject every drift,
denial, malformed verifier result, or postcondition failure with zero mutation
or bounded rollback. Keep start, stop, restart, uninstall, and every generic
family fail-closed. Make `service open` read-only: it may open a healthy service
or tell the operator to run explicit install, but never repair implicitly.

## Dependencies

AR-143 and ADR-0096 define the non-exporting, action-specific presence
boundary. AR-161 still owns signed/licensed production delivery of the native
helper. AR-194 owns cross-interpreter inspection and needs this action for its
final attended repair evidence.

## Acceptance

- [ ] Only exact non-dry-run `dashboard service install` can select the new
  prepared action; adjacent commands and malformed shapes remain unavailable.
- [ ] Preparation is write-free and binds every service, runtime, launcher,
  configuration, owner, and desired-state identity shown to the operator.
- [ ] Denial, malformed verifier output, or any pre-lock/post-lock drift
  dispatches no persistent change.
- [ ] A verified unchanged plan installs or repairs under the service lock and
  proves exact task, manifest, runtime, ownership, and reachability
  postconditions with bounded rollback on failure.
- [ ] Healthy no-op and `service open` paths do not request presence or mutate;
  unhealthy open returns precise attended repair guidance.
- [ ] Focused Python/C++ protocol tests pass and an attended Windows Hello
  canary repairs the exact installed service.
