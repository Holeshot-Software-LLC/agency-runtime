---
title: "Separate immediate host control from native plugin lifecycle"
status: accepted
category: decisions
created: 2026-07-11
updated: 2026-07-11
tags: [operations, hosts, controls, sqlite]
related:
  - docs/roadmap/issue-AR-03-supported-host-integrations.md
  - docs/roadmap/issue-AR-04-runtime-controls.md
  - docs/decisions/0010-one-command-install-and-reversible-toggle.md
  - docs/decisions/0024-native-host-packages-and-minimal-bridges.md
  - docs/decisions/0028-host-support-maturity-and-reversible-install.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
id: ADR-0034
type: decision
deciders: []
---

# ADR-0034: Separate immediate host control from native plugin lifecycle

## Context

Disabling a native plugin can require a host restart and can remove the very
command surface needed to turn Agency Runtime back on. Host registries also
express installed, registered, enabled, and loaded state differently. Using
native lifecycle commands as the only runtime switch cannot provide one
immediate and reversible behavior across already-running integrations.

The existing SQLite store already provides a durable, process-shared boundary
for runtime evidence. A control stored only in one adapter instance or one CLI
process would not survive restarts and would drift from dashboard and host-chat
status.

## Decision

Store a host-scoped soft-control value in the canonical SQLite database. The
default is enabled for backward compatibility. Every adapter boundary checks
the current value before routing, recording tool evidence, accepting model
telemetry, finalizing a response, or verifying it. Disabling does not delete
roster, configuration, evidence, native files, or registration state.

Make `agency on`, `agency off`, and `agency status` use this persistent soft
control by default. Keep native enablement and disablement available only
through an explicit `--native` lifecycle request. Status reports runtime
control, native registration and enablement, and effective state separately;
unknown native evidence remains `unverified` rather than becoming true.

Expose the same control through host-native commands or the generated
conversation skill and MCP boundary. Mutations require exact confirmations at
remote control surfaces. Native registry changes, restart requirements, and
live canary claims remain separate facts.

## Consequences

- Subsequent hook boundaries in a loaded host observe disablement without
  deleting or unloading the integration.
- An event already past a checked boundary is not forcibly cancelled; each
  later boundary checks again.
- CLI, dashboard, MCP, and host commands share one persistent source of truth.
- Native lifecycle operations remain available for maintenance but cannot be
  confused with immediate runtime control.
- SQLite schema migration and concurrent access become part of the control
  availability contract.

## Alternatives

- Rename or remove plugin files. Rejected because it is host-specific,
  restart-dependent, and destroys the in-conversation recovery surface.
- Keep an in-memory flag in each adapter. Rejected because processes and host
  sessions would disagree and restarts would reset it.
- Rewrite each native registry for every toggle. Rejected because registry
  semantics differ by host and current load state is not guaranteed to change.
- Delete runtime state when disabling. Rejected because control and retention
  are independent operator choices.

## Provenance

AR-03 and AR-04 record the host contract, control implementation, and live
evidence boundary. The implementation commit is linked after final validation.
