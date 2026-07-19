---
title: "AR-57: Add a durable Agency-wide master switch"
status: done
category: roadmap
created: 2026-07-16
updated: 2026-07-16
tags: [operations, control-plane, cli, dashboard, windows, security]
related:
  - docs/decisions/0053-durable-fail-enabled-master-control.md
  - docs/decisions/0034-persistent-soft-host-control.md
  - docs/THREAT_MODEL.md
  - docs/TROUBLESHOOTING.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: operations
issue_id: AR-57
priority: p0
tracker_url: "https://github.com/Holeshot-Software-LLC/agency-runtime/issues/58"
depends_on: [AR-51]
blocks: [AR-74, AR-77]
---

# AR-57: Add a durable Agency-wide master switch

## Problem

Host-scoped soft controls are useful for operating one integration, but they do
not provide a trustworthy Agency-on versus Agency-off comparison. A control
that is read only after configuration, SQLite, routing, or correlation starts
can still shape a supposedly unassisted response and can be inaccessible from
a restricted host process on Windows.

## Current state

Agency now has one durable per-user master state, separate from host controls
and normal configuration. `agency off --global` and `agency on --global` change
that state, and the authenticated dashboard exposes the same revision-checked
switch. Every host boundary checks it before Store creation, turn correlation,
routing, prompt activation, delegation, model evidence, or finalization.
Dashboard host-toggle responses read that server's bound control identity and
cannot silently fall back to the process user's default home.

## Approach

Persist a small versioned document at
`~/.agency-runtime/run/control.json`. Publish updates atomically under an
owner-private lock with a monotonic generation. Treat a genuinely absent or
invalid document as enabled, so deleting or corrupting the control cannot
silently suppress enforcement. Let a restricted Windows reader consume only
the canonical path after proving stable real-file identities and the absence of
rights that could alter the file or its parent chain. When direct mutation is
unavailable, let the CLI use the authenticated local dashboard service as a
least-privilege broker.

## Dependencies

AR-04 established persistent host controls, and AR-51 made their all-host CLI
contract honest. This item adds a separate cross-host master boundary; it does
not replace either host-scoped soft control or native plugin lifecycle.

## Acceptance

- [x] CLI and dashboard read and mutate one durable master generation.
- [x] `--global` is explicit and cannot be combined with native lifecycle control.
- [x] Disabled hosts bypass before Store, correlation, routing, delegation, and evidence work.
- [x] Existing configuration, roster, history, and native registration remain intact.
- [x] Missing, malformed, or unverifiable control state fails enabled.
- [x] Restricted Windows reads require exact canonical identity and read-only integrity proof.
- [x] Direct CLI mutation falls back only to the authenticated loopback dashboard broker.
- [x] Operators are told to start a fresh host session for a clean A/B comparison.
- [x] Host-toggle responses project the same server-bound master generation as the header.
