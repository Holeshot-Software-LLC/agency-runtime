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

The CLI exposes `agency on` and `agency off` with `--dry-run` and JSON output.
Both use the selected host's native plugin lifecycle; they do not rename one
assumed Python file and do not touch configuration, roster, runtime evidence, or
backups. Install is atomic, retains timestamped backups, and supports
`install --rollback` with a native refresh where the host contract permits it.

There is no uniform status subcommand or in-conversation `/agency on|off`
command. The controls report when a restart is required and do not claim that
an already-running host reloads state without native evidence.

The 2026-07-11 deterministic suite covers fail-closed rollback, dry-run,
backup selection, failure protocols, and host-aware lifecycle construction. It
does not establish live reload or chat-command behavior, so the remaining
criteria stay open.

## Approach

Add one status view that reports the same native maturity used by doctor and the
dashboard. Prove live enable/disable behavior where a host supports reload, and
otherwise require and report restart. Add host-native `/agency on`, `/agency
off`, and status handling only for integrations proven by `AR-03`.

## Dependencies

Depends on `AR-03`, because each control must use the host's verified integration mechanism rather than assume a common plugin file.

## Acceptance

- [ ] CLI enable, disable, and status work for every verified host.
- [x] Native and Python plugin artifacts are handled by host-aware logic.
- [ ] Disable takes effect in an already-running supported host where the host contract permits it.
- [x] Enabled state uses the persistent native registry without deleting runtime or roster data.
- [ ] Supported chat commands confirm the resulting state and are covered by tests.
