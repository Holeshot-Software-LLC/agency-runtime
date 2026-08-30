---
title: "Remove Agency-owned Windows Hello and use harness-native trust"
status: superseded
category: decisions
created: 2026-07-28
updated: 2026-07-28
tags: [security, windows, operator-presence, host-integrations, dashboard]
related:
  - docs/roadmap/issue-AR-197-remove-agency-owned-windows-hello.md
  - docs/roadmap/issue-AR-196-authorize-prepared-dashboard-service-repair.md
  - docs/roadmap/handoffs/issue-AR-196.md
  - docs/roadmap/issue-AR-143-require-operator-presence-for-controls.md
  - docs/roadmap/issue-AR-161-sign-and-license-windows-operator-presence-delivery.md
  - docs/roadmap/issue-AR-185-bind-codex-activation-verification.md
  - docs/roadmap/issue-AR-189-add-owned-host-integration-uninstall.md
  - docs/decisions/0090-model-facing-control-paths-are-read-only.md
  - docs/decisions/0096-require-operator-presence-for-persistent-controls.md
  - docs/decisions/0109-prepare-dashboard-service-repair-before-operator-presence.md
supersedes:
  - docs/decisions/0096-require-operator-presence-for-persistent-controls.md
  - docs/decisions/0109-prepare-dashboard-service-repair-before-operator-presence.md
superseded_by: docs/decisions/0111-install-the-applicable-suite-by-default.md
id: ADR-0110
type: decision
deciders: [maintainers]
---

# ADR-0110: Remove Agency-owned Windows Hello and use harness-native trust

## Context

Agency Runtime is primarily an advisory plugin integration for Codex and other
harnesses. ADR-0096 added a packaged Windows Hello verifier because an agent can
invoke the same CLI that an operator can invoke. That independent ceremony was
then applied to routine plugin refresh, roster rollback, host uninstall, and a
proposed dashboard-service repair path.

The result duplicates harness-native registration and trust, complicates
packaging and signing, and couples the core plugin demo to an optional Windows
service. A bounded dashboard-service attempt also proved that one presence
prompt cannot faithfully authorize task registration, process lifecycle,
runtime publication, credential descriptors, Store maintenance, and rollback
as though they were one atomic mutation.

## Decision

Remove the Agency-owned Windows Hello verifier and its action-specific protocol
from the product. Do not replace it with a static phrase, exported bearer,
environment variable, or model-callable confirmation.

Routine harness-plugin install, refresh, enablement, disablement, and trust use
the harness's native lifecycle and trust surface. Agency may prepare and verify
owned plugin artifacts, but it does not add a second OS-presence ceremony and
does not override the harness's delegation model. Codex hook trust remains a
Codex decision.

Model-facing MCP, hook, broker, and dashboard paths remain read-only for
persistent Agency governance or data mutations. Existing positive mutations
that depended only on Agency's Windows Hello result return to fail-closed until
they are removed, converted to a harness-native lifecycle operation, or given a
smaller architecture that does not export authority to models.

The optional dashboard service is explicit opt-in and is not part of harness
plugin activation or demo acceptance. Its lifecycle may be redesigned later as
a real multi-phase service transaction, but it does not block proving that the
Agency plugin loads, routes, and delegates correctly.

## Consequences

- Routine plugin lifecycle loses a redundant prompt and follows the harness's
  own registration, enablement, and trust semantics.
- The native verifier executable, source, provenance, build, distribution,
  signing, and action protocols become removal work rather than release gates.
- Roster rollback, owned host uninstall, and dashboard-service mutation remain
  unavailable until their authority boundaries are separately simplified.
- Dashboard and MCP monitoring stay available without acquiring mutation
  authority.
- Existing exact planning, ownership, locking, rollback, and postcondition code
  remains useful but cannot claim authorization by itself.

## Alternatives

- **Finish every action-specific Windows Hello protocol.** Rejected because it
  duplicates harness trust and turns each local lifecycle operation into a
  bespoke security product.
- **Use a confirmation flag or typed phrase.** Rejected because an agent can
  supply the same value and it creates no independent authority boundary.
- **Allow dashboard or MCP mutations directly.** Rejected because model-facing
  credentials remain observation authority, not persistent write authority.
- **Remove the dashboard entirely.** Deferred; monitoring remains useful, while
  its optional persistent service is decoupled from the plugin path.
