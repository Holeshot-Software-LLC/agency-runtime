---
title: "Prepare dashboard-service repair before operator presence"
status: superseded
category: decisions
created: 2026-07-28
updated: 2026-07-28
tags: [dashboard, service, windows, security, operator-presence]
related:
  - docs/roadmap/issue-AR-197-remove-agency-owned-windows-hello.md
  - docs/roadmap/issue-AR-196-authorize-prepared-dashboard-service-repair.md
  - docs/roadmap/issue-AR-143-require-operator-presence-for-controls.md
  - docs/roadmap/issue-AR-194-inspect-owned-service-runtimes-across-python-versions.md
  - docs/decisions/0031-optional-user-dashboard-service-and-shared-configuration.md
  - docs/decisions/0051-bind-dashboard-runtime-publication-to-validated-filesystem-identities.md
  - docs/decisions/0096-require-operator-presence-for-persistent-controls.md
  - docs/THREAT_MODEL.md
  - docs/TROUBLESHOOTING.md
  - agency_runtime/core/operator_presence.py
  - agency_runtime/core/windows_operator_presence.py
  - agency_runtime/core/dashboard_service_install.py
  - docs/roadmap/handoffs/issue-AR-196.md
supersedes: []
superseded_by: docs/decisions/0110-remove-agency-owned-windows-hello.md
id: ADR-0109
type: decision
deciders: [maintainers]
---

# ADR-0109: Prepare dashboard-service repair before operator presence

## Context

ADR-0096 deliberately leaves a persistent mutation unavailable until its exact
resolved state and consequence can be bound to a non-exporting OS verification.
The dashboard service has inspection, ownership, immutable-runtime, rollback,
and locking machinery, but its CLI currently reaches only the unavailable
generic verifier. Reusing another action's Windows Hello result or verifying a
generic namespace digest would not bind the scheduled task, manifest, runtime,
launcher, Python, configuration, or current-to-target transition.

The existing installer also prepares a private package runtime before taking
the service lock. Preparation can publish files, so it cannot be run before
human verification in a transaction that claims the pre-verification phase is
write-free. `dashboard service open` compounds the problem by attempting
implicit repair and therefore requiring mutation authority even when the
operator only wants to open an already healthy loopback dashboard.

## Decision

Admit one additional positive operator-presence action on supported Windows:
idempotent dashboard-service install-or-repair. Keep every other service
mutation unavailable until separately designed.

The coordinator first prepares an immutable, write-free primitive binding. It
binds the current user, effective configuration identity, manifest identity or
absence, exact owned task definition and state, runtime descriptor and port,
selected Python and launcher identities, desired task/manifest/runtime plan,
private publication plan, action, transition, and consequence. A healthy exact
no-op may recheck and return without asking for presence. Otherwise the native
helper displays the human-readable current-to-target transition and returns a
nonce- and binding-matched result only inside the synchronous call stack.

After verification, acquire the service lock, fully reprepare and compare the
same binding, publish the private runtime, revalidate executable identities,
perform the owned Windows transaction, and require exact postconditions.
Denial, malformed native output, drift, publication failure, task failure, or
postcondition failure authorizes no adjacent action and produces either zero
mutation or the existing bounded identity-checked rollback. Do not expose a
public prepare/commit API, injectable verifier, generic readiness boolean, or
transferable authorization receipt.

Make dashboard-service open a read-only operation. It may open a proven healthy
service; otherwise it reports the exact attended install command. It never
repairs, starts, registers, or rewrites state implicitly.

## Consequences

- The documented attended Windows service repair path can become usable
  without weakening the model-facing dashboard or generic CLI boundary.
- A Windows Hello success for roster, Codex, host uninstall, or dashboard
  service cannot authorize any other operation.
- Preparation may cost additional read-only inspection because the complete
  plan is recomputed after the service lock; that is the intended TOCTOU
  defense.
- Healthy open and no-op flows avoid unnecessary presence prompts and
  persistent writes.
- Unsupported platforms and start, stop, restart, and uninstall remain visibly
  unavailable rather than falling back to process ownership, a TTY, or a
  confirmation phrase.
- Signed/licensed native delivery and an attended live Windows Hello canary
  remain release gates independent of source-level correctness.

## Alternatives

- **Reuse the generic operator-presence stub.** Rejected because an opaque
  family digest does not bind resolved service state or the real transaction.
- **Reuse Codex-refresh or host-uninstall authority.** Rejected because native
  verification is action-specific and non-transferable.
- **Prepare the runtime before verification.** Rejected because private runtime
  publication is already a persistent write.
- **Keep implicit repair in `service open`.** Rejected because a read/open
  request should not acquire mutation authority or surprise the operator.
- **Allow all service lifecycle verbs in one action.** Rejected because each
  current-to-target transition needs its own reviewed state and consequence.
