---
title: "AR-196: Authorize prepared dashboard-service install and repair"
status: wont_do
category: roadmap
created: 2026-07-28
updated: 2026-07-30
tags: [windows, dashboard, service, security, operator-presence]
related:
  - docs/roadmap/issue-AR-204-reconcile-readme-story-contract.md
  - docs/decisions/0117-unify-owner-control-authority.md
  - docs/decisions/0110-remove-agency-owned-windows-hello.md
  - docs/roadmap/issue-AR-197-remove-agency-owned-windows-hello.md
  - docs/decisions/0031-optional-user-dashboard-service-and-shared-configuration.md
  - docs/decisions/0051-bind-dashboard-runtime-publication-to-validated-filesystem-identities.md
  - docs/decisions/0096-require-operator-presence-for-persistent-controls.md
  - docs/decisions/0109-prepare-dashboard-service-repair-before-operator-presence.md
  - docs/roadmap/issue-AR-143-require-operator-presence-for-controls.md
  - docs/roadmap/issue-AR-161-sign-and-license-windows-operator-presence-delivery.md
  - docs/roadmap/issue-AR-194-inspect-owned-service-runtimes-across-python-versions.md
  - docs/roadmap/handoffs/issue-AR-196.md
  - agency_runtime/core/dashboard_service_install.py
  - agency_runtime/core/dashboard_service_core.py
  - agency_runtime/cli/service_commands.py
  - tests/test_cli_owner_authority.py
  - tests/test_dashboard_service.py
supersedes: []
superseded_by: docs/roadmap/issue-AR-204-reconcile-readme-story-contract.md
type: issue
epic: security
issue_id: AR-196
priority: p0
tracker_url: null
depends_on: [AR-143, AR-161, AR-197]
blocks: [AR-194]
---

# AR-196: Authorize prepared dashboard-service install and repair

> Superseded on 2026-07-30 by [AR-204](issue-AR-204-reconcile-readme-story-contract.md)
> and [ADR-0117](../decisions/0117-unify-owner-control-authority.md). The
> dashboard service remains ownership-, identity-, lock-, and postcondition-
> checked, but it no longer requires a separate human-presence ceremony.
> `dashboard service open` may repair or start the owned service.

## Problem

Every persistent dashboard-service command reaches the generic
operator-presence boundary, whose OS verifier is intentionally unavailable.
The commands therefore fail closed before their handlers run. This is secure,
but it makes an owned stale service impossible to install or repair through the
documented attended CLI path. `dashboard service open` is also classified as a
mutation because it may auto-repair, so even a healthy read/open path is gated.

## Current state

Exact installed revision `8507778` can inspect the Python-3.13-owned service
from the Python-3.10 CLI and truthfully reports it installed, enabled, inactive,
unreachable, stale, and repair-recommended. Running the documented repair
command returns `unavailable: a non-exporting OS operator-presence verifier is
not available` and dispatches no mutation. Existing Windows Hello support is
action-specific to roster rollback, existing Codex refresh, and owned host
uninstall; its result cannot safely authorize adjacent service state.

A bounded implementation attempt proved that this is not merely a missing
verifier action. Dashboard activation spans task registration, launcher-runtime
publication, owner and Codex-broker credential descriptors, process identity,
Store readiness, and retention maintenance. The draft also exposed unsafe
rollback claims for surviving fresh or repaired workers, an opaque native
prompt that omitted exact targets and material consequences, and a stable raw
configuration digest that could depend on plaintext secrets. The entire draft
was removed. The pushed source remains fail-closed and the exact findings and
next package are captured in the active recovery capsule. Tracker creation
remains pending explicit authorization.

## Approach

First decide and document the smaller product boundary: routine harness-plugin
install, refresh, enablement, and trust should normally use each harness's
native lifecycle rather than Agency adding a second Windows Hello ceremony.
The optional dashboard service must be an explicit, separate opt-in and must
not block plugin activation or the CEO demo. This requires a superseding ADR
before implementation because ADR-0096 and ADR-0109 currently govern the wider
presence requirement.

If the persistent dashboard service remains a supported positive mutation,
model it as an explicit two-phase Windows activation transaction rather than a
verifier wrapper. The worker first enters a bounded bootstrap state that cannot
initialize, migrate, prune, or otherwise write the Store and cannot publish a
model-facing broker credential. After exact task, process, runtime, manifest,
owner-descriptor, and loopback-health proof, the coordinator commits one
activation transition that admits ordinary service behavior. Failure must stop
and identify the exact candidate process, prove both runtime descriptors
cleared, restore the exact prior task and manifest when present, and report any
retained immutable launcher cache as an authorized consequence rather than a
full rollback.

Keep start, stop, restart, uninstall, active-but-drifted repair, and every
generic family fail-closed until separately modeled. Make `service open`
read-only: it may open a healthy service or tell the operator to run explicit
install, but never repair implicitly.

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
