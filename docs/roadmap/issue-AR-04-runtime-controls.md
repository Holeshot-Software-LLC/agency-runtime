---
title: "AR-04: Add durable runtime controls"
status: open
category: roadmap
created: 2026-07-10
updated: 2026-07-10
tags: [operations, adapters]
related:
  - docs/decisions/0010-one-command-install-and-reversible-toggle.md
  - docs/decisions/0024-native-host-packages-and-minimal-bridges.md
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

The CLI exposes `agency on` and `agency off`. The implementation toggles `__init__.py`, which covers generated Python plugins but not the native OpenClaw `index.js` artifact. No chat or slash command exists, and there is no shared runtime-enabled flag that an already-loaded adapter checks.

## Approach

Introduce one persisted, per-host enabled state in configuration or the runtime store and have every adapter short-circuit consistently when disabled. Make CLI controls update that state and manage the correct host artifact when restart persistence requires it. Add host-native `/agency on`, `/agency off`, and status handling only for integrations proven by `AR-03`.

## Dependencies

Depends on `AR-03`, because each control must use the host's verified integration mechanism rather than assume a common plugin file.

## Acceptance

- [ ] CLI enable, disable, and status work for every verified host.
- [ ] Native and Python plugin artifacts are handled by host-aware logic.
- [ ] Disable takes effect in an already-running supported host where the host contract permits it.
- [ ] Enabled state survives restart without deleting runtime or roster data.
- [ ] Supported chat commands confirm the resulting state and are covered by tests.
