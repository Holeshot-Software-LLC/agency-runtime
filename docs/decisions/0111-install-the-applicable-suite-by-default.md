---
title: "Install the applicable suite by default"
status: superseded
category: decisions
created: 2026-07-28
updated: 2026-07-28
tags: [installation, host-integrations, dashboard, discovery, usability]
related:
  - docs/roadmap/issue-AR-198-install-applicable-suite-by-default.md
  - docs/roadmap/issue-AR-197-remove-agency-owned-windows-hello.md
  - docs/decisions/0010-one-command-install-and-reversible-toggle.md
  - docs/decisions/0110-remove-agency-owned-windows-hello.md
supersedes:
  - docs/decisions/0110-remove-agency-owned-windows-hello.md
superseded_by: docs/decisions/0117-unify-owner-control-authority.md
id: ADR-0111
type: decision
deciders: [maintainers]
---

# ADR-0111: Install the applicable suite by default

## Context

Agency Runtime is distributed as one suite whose useful local surface includes
the Store, bundled roster, applicable harness integrations, and dashboard.
Requiring users to opt into ordinary components makes installation state depend
on remembered flags and coupled failure handling. ADR-0110 correctly removed
Agency-owned Windows Hello and selected harness-native trust, but incorrectly
made the dashboard an explicit opt-in.

## Decision

Bare `agency install` is the full-suite installation command. It detects the
current operating system and every installed supported harness, initializes the
applicable Agency-owned core state, installs or refreshes every detected native
integration, and installs the dashboard service when supported.

Options narrow that default. `--agent <host>` limits harness scope,
`--no-dashboard` excludes the dashboard, and existing dry-run and rollback
options retain their exact meanings. `--all` remains a compatible explicit
spelling of automatic harness discovery; it is no longer required for the
default behavior.

Each selected component reports its own outcome. A dashboard preflight or
installation failure does not suppress an otherwise valid harness transaction,
and a harness failure does not prevent later selected harnesses from being
attempted. The aggregate result distinguishes complete success, partial
success, and complete failure. A component remains fail-closed within its own
transaction and cannot claim success without its postconditions.

Harness registration, enablement, and trust use each harness's native lifecycle.
The installer does not recreate Agency-owned Windows Hello or grant persistent
mutation authority to MCP, hooks, broker, or dashboard request paths.

## Consequences

- The shortest documented command installs the useful applicable product.
- Users opt out of components they do not want instead of discovering hidden
  opt-ins after installation.
- Component-level failures remain visible without erasing successful work in
  independent components.
- Explicit host selectors remain useful for repair and controlled testing.
- A default install may make more local changes than the former narrow path, so
  dry-run output and structured component results must remain complete.

## Alternatives

- **Keep the dashboard opt-in.** Rejected because it makes the default command
  install only part of the product and contradicts the full-suite model.
- **Abort all work on the first component failure.** Rejected because unrelated
  harness and dashboard transactions do not share one atomic commit boundary.
- **Install every supported harness whether present or not.** Rejected because
  auto-discovery should select applicable local integrations, not fabricate
  absent host installations.
