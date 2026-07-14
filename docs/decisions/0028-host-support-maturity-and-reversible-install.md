---
title: "Separate host contract coverage from live support maturity"
status: accepted
category: decisions
created: 2026-07-10
updated: 2026-07-11
tags: [hosts, installation, operations]
related:
  - docs/roadmap/issue-AR-03-supported-host-integrations.md
  - docs/roadmap/issue-AR-04-runtime-controls.md
  - docs/roadmap/issue-AR-07-public-release-readiness.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
id: ADR-0028
type: decision
deciders: []
---

# ADR-0028: Separate host contract coverage from live support maturity

## Context

The v1 product target is Codex, Claude Code, Hermes, and OpenClaw on native
Windows and Ubuntu/WSL. Generating a syntactically valid plugin is useful
contract evidence, but it does not prove that a particular host executable
exists, accepted registration, enabled the plugin, loaded hooks, or completed a
canary. A stale configuration directory can also outlive the host executable.

Installation must remain safe when host CLIs fail midway, change native caches,
or require a restart. One generic file toggle cannot represent all four native
lifecycle contracts.

## Decision

Report deterministic host-contract coverage and live installation maturity as
separate facts. The live state machine is evidence-based:

`absent` → `stale-config` or `host-discovered` → `staged-not-registered` →
`registered-disabled` / `registered-enablement-unverified` →
`enabled-runtime-unverified` → `runtime-verified`.

Expose the underlying `discovered`, `staged`, `registered`, `enabled`, `loaded`,
and `canary` fields so callers do not have to reverse-engineer the summary.
Unknown values remain unknown. Current native state markers or an executable
may establish discovery; a bare directory may not. Filesystem staging may not
establish registration, and cold inventory may not establish runtime loading.

Use the native lifecycle for registration and enable/disable. Stage the complete
managed bundle atomically, retain the previous managed tree under a timestamped
backup, provide a write-free `--dry-run`, and restore with `install --rollback`.
Native-step failure is a nonzero partial failure with the failed step and backup
path. Never restart a host automatically; pause OpenClaw installation when a
live gateway would require a restart.

Contract tests use explicit temporary home/database boundaries and injected
native command runners. They cover Windows command shims and direct POSIX argv,
but they must be described as contract evidence until a real host canary proves
runtime behavior in the claimed environment.

## Consequences

- Installer, doctor, dashboard, tests, and documentation share one maturity
  vocabulary.
- A truthful install can end at staged or enabled-but-unverified instead of
  printing a false success claim.
- Each host keeps its own native package format and lifecycle commands.
- Operators can preview, recover, and audit changes without deleting roster or
  runtime data.
- Public support matrices require dated live evidence in addition to green
  deterministic tests.
- Some hosts may remain v1 targets without being advertised as live-verified.

## Alternatives

- Call every generated bundle supported. Rejected because file presence does
  not prove discovery or execution.
- Use only `verified`, `experimental`, and `planned`. Rejected as the sole model
  because it hides which native boundary is actually proven.
- Rename or delete one plugin file to toggle every host. Rejected because native
  registries, marketplaces, and runtime caches differ.
- Restart hosts automatically. Rejected because it can interrupt user work and
  exceeds the installer's authority.

## Provenance

The production-readiness refactor added conservative discovery, native bundle
registration, separate maturity fields, atomic staging, retained backups,
rollback, native on/off controls, and deterministic Windows/POSIX lifecycle
tests. The implementation commit is recorded through the worklog after it is
created.
