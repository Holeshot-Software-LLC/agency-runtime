---
title: "Use a durable fail-enabled master control before every host boundary"
status: accepted
category: decisions
created: 2026-07-16
updated: 2026-07-20
tags: [operations, control-plane, security, cli, dashboard, windows]
related:
  - docs/roadmap/issue-AR-57-durable-agency-wide-master-switch.md
  - docs/roadmap/issue-AR-74-broker-restricted-windows-host-controls.md
  - docs/roadmap/issue-AR-77-validate-brokered-control-transition-receipts.md
  - docs/decisions/0034-persistent-soft-host-control.md
  - docs/decisions/0039-fail-before-dacl-mutation-under-restricted-windows-tokens.md
  - docs/decisions/0076-bind-isolated-canaries-to-explicit-agency-modes.md
  - docs/THREAT_MODEL.md
  - docs/TROUBLESHOOTING.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
id: ADR-0053
type: decision
deciders: [maintainers]
---

# ADR-0053: Use a durable fail-enabled master control before every host boundary

## Context

Host-scoped SQLite controls intentionally leave each native integration
installed, but they are too late and too narrow for a trustworthy whole-product
A/B test. Reading a switch after Store creation or correlation may already
shape the turn. A normal configuration field has the same problem and may be
unreadable from a restricted Windows host even when the host can safely read a
small canonical control file.

The switch itself is an enforcement boundary. A local actor must not be able to
delete, replace, corrupt, or redirect it and thereby turn Agency off silently.
At the same time, operators need one reversible control in both the CLI and
dashboard without unregistering plugins or erasing history.

## Decision

Keep the master state in the versioned owner-private document
`~/.agency-runtime/run/control.json`, separate from normal configuration,
SQLite host controls, and native plugin lifecycle. A missing document means
enabled. Any malformed, unreadable, unsafe, or unverifiable state also fails
enabled on the enforcement fast path and remains visible as a diagnostic fault
on strict control surfaces.

Publish changes under an owner-private lock with compare-and-swap generation,
bounded JSON, exact schema validation, a random exclusive temporary file,
`fsync`, atomic replacement, and a verified postcondition. `agency on --global`
and `agency off --global` use that writer. The authenticated loopback dashboard
uses the same generation and may broker a CLI write when a restricted process
cannot obtain the required Windows control rights.

Every host adapter and protocol boundary checks the master state before Store
construction, turn correlation, routing, prompt activation, delegation, model
receipt handling, or finalization. Off means pass through the host's content
without creating new Agency evidence; it does not uninstall native packages,
delete configuration, mutate roster state, or erase historical evidence.
Normal MCP, HTTP, hook, Hermes, roster search/route/explain, and public
delegation surfaces return that stable bypass before validating their ordinary
payloads or opening configuration and SQLite. Master status remains a
Store-free projection; explicit host/master status and control tools remain the
small administrative exception needed to turn the runtime back on.

On Windows, a restricted host may use a reduced-privilege reader only for the
canonical home-relative path. That reader requires stable real file and parent
identities and proves that the current token has none of the individual rights
that could alter or replace them. It never treats a wildcard capability SID as
equivalent to the owning user. If integrity cannot be proven, enforcement is
on.

Operators must start a fresh host session after changing the master state when
they want a clean with-Agency versus without-Agency comparison. The durable
state takes effect at each boundary, but an existing model context cannot
unlearn instructions already injected earlier in its session.

## Consequences

- One switch covers Codex, Claude Code, Hermes, OpenClaw, MCP, HTTP, LiteLLM,
  delegation, and the dashboard without conflating their native lifecycle.
- Deletion or corruption cannot manufacture an enforcement-off state.
- A restricted Windows host can honor a proven read-only state without being
  granted permission to mutate it.
- CLI and dashboard mutations detect stale generations instead of overwriting
  a concurrent operator choice.
- Dashboard host listings and toggle responses project the same server-bound
  control identity instead of consulting a default-home fallback.
- Off-mode response behavior is intentionally minimal, and no new Agency audit
  evidence is created until the switch is re-enabled.
- Off-mode status, route, search, and delegation results do not fabricate a
  trace or initialize otherwise-unused runtime state.
- A fresh host session is required for experimentally clean A/B results.

## Alternatives

- Add a normal configuration field. Rejected because config loading is too late
  for a complete bypass and can itself create or consult runtime state.
- Reuse every host's SQLite soft control. Rejected because it requires Store
  access, is host-scoped, and cannot guarantee a pre-correlation bypass.
- Treat missing or invalid state as off. Rejected because deletion or
  corruption would become a trivial enforcement-suppression attack.
- Uninstall and reinstall every native integration for each comparison.
  Rejected because it is slow, destructive to experimental parity, and not an
  appropriate operational switch.
