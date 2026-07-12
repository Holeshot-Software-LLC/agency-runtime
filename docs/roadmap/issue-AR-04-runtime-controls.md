---
title: "AR-04: Add durable runtime controls"
status: in_progress
category: roadmap
created: 2026-07-10
updated: 2026-07-11
tags: [operations, adapters]
related:
  - docs/decisions/0010-one-command-install-and-reversible-toggle.md
  - docs/decisions/0024-native-host-packages-and-minimal-bridges.md
  - docs/decisions/0028-host-support-maturity-and-reversible-install.md
  - docs/decisions/0034-persistent-soft-host-control.md
  - docs/decisions/0036-capability-bound-host-canary-attestations.md
supersedes: []
superseded_by: null
type: issue
epic: operations
issue_id: AR-04
priority: p1
tracker_url: "https://github.com/Holeshot-Software-LLC/agency-runtime/issues/4"
depends_on: [AR-03]
blocks: [AR-07]
---

# AR-04: Add durable runtime controls

## Problem

Users need to enable or disable Agency Runtime immediately and persistently from both the CLI and supported host conversations. Renaming one plugin file is host-specific, may require a restart, and cannot provide a uniform runtime state.

## Current state

The CLI now exposes `agency status` plus `agency on` and `agency off` with
`--dry-run` and JSON output. The default transition is an immediate,
host-scoped soft control persisted in SQLite; the same already-instantiated
adapter reads it at every boundary, stops cleanly after `off`, and resumes
after `on` without changing existing evidence or roster data.

`--native` explicitly selects the host plugin lifecycle. It requires native
inventory to prove the postcondition, distinguishes unknown enablement from
success, preserves timestamped backups, and remains rollback-aware.

Hermes and OpenClaw generated packages expose direct control commands. Codex and
Claude generated control skills use exact-confirmed MCP status/control tools.
The dashboard, CLI, MCP, and generated surfaces share the same persistent
record and report native, runtime, and effective state separately.

The 2026-07-11 deterministic suite covers same-instance off/status/on
round-trips, persistence across store restarts, unchanged non-control data,
generated host commands, MCP confirmations, fail-closed native postconditions,
rollback, and Windows/POSIX lifecycle construction. It does not establish
execution inside a live host conversation or host reload behavior, so those
criteria stay open.

## Approach

Keep one status model across CLI, dashboard, MCP, and generated host surfaces.
Use soft control for immediate adapter-boundary behavior and explicit native
lifecycle operations for registry changes. Prove live enable/disable behavior
where a host supports reload, and otherwise require and report restart.

## Dependencies

Depends on `AR-03`, because each control must use the host's verified integration mechanism rather than assume a common plugin file.

## Acceptance

- [ ] CLI enable, disable, and status work for every verified host.
- [x] Native and Python plugin artifacts are handled by host-aware logic.
- [ ] Disable takes effect in an already-running supported host where the host contract permits it.
- [x] Soft state persists without deleting runtime or roster data; explicit native state uses the host registry.
- [x] Generated chat-command and MCP control surfaces confirm the resulting state in deterministic tests.
- [ ] Control commands execute successfully inside every live verified host.
