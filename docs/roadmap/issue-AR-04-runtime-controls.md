---
title: "AR-04: Add durable runtime controls"
status: done
category: roadmap
created: 2026-07-10
updated: 2026-07-12
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

The deterministic suite covers same-instance off/status/on round-trips,
persistence across store restarts, unchanged non-control data, generated host
commands, MCP confirmations, fail-closed native postconditions, rollback, and
Windows/POSIX lifecycle construction.

On 2026-07-12, direct CLI `off` and `on` completed against the installed native
Codex profile and restored the enabled state. A separate externally isolated
Codex 0.144.1 profile then loaded the installed `$agency` skill and MCP server,
called `agency.host_status`, exact-confirmed `DISABLE codex`, observed the
effective state change immediately in the same live turn, exact-confirmed
`ENABLE codex` in a reciprocal turn, and observed the final enabled state.
Read-only SQLite inspection independently matched the final MCP record. The
profile, HOME, configuration, and Agency state were temporary; the real user
database was not touched.

Codex `exec` cannot present its interactive side-effect approval prompt, so the
bounded proof used its one-invocation approval/sandbox bypass with shell tools
disabled and an exact task limited to the Agency MCP controls. That bypass is
canary-only evidence, never installation policy. Other v1 hosts were absent and
remain contract-covered rather than live-verified.

## Approach

Keep one status model across CLI, dashboard, MCP, and generated host surfaces.
Use soft control for immediate adapter-boundary behavior and explicit native
lifecycle operations for registry changes. Prove live enable/disable behavior
where a host supports reload, and otherwise require and report restart.

## Dependencies

Depends on `AR-03`, because each control must use the host's verified integration mechanism rather than assume a common plugin file.

## Acceptance

- [x] CLI enable, disable, and status work for every verified host.
- [x] Native and Python plugin artifacts are handled by host-aware logic.
- [x] Disable takes effect in an already-running supported host where the host contract permits it.
- [x] Soft state persists without deleting runtime or roster data; explicit native state uses the host registry.
- [x] Generated chat-command and MCP control surfaces confirm the resulting state in deterministic tests.
- [x] Control commands execute successfully inside every live verified host.
