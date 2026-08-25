---
title: "Bind OpenClaw installed-copy provenance"
status: open
category: roadmap
created: 2026-08-21
updated: 2026-08-23
tags: [openclaw, uninstall, provenance, reliability]
related:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/handoffs/issue-AR-119.md
  - agency_runtime/core/installer_uninstall.py
  - tests/test_installer_registration.py
supersedes: []
superseded_by: null
type: issue
epic: install
issue_id: AR-270
priority: p0
tracker_url: null
depends_on: []
blocks: []
---

# AR-270: Bind OpenClaw installed-copy provenance

## Problem

OpenClaw `2026.7.1-2` reports a path-installed plugin with a native installed
copy under its extensions directory and a distinct `install.sourcePath` that
points at Agency's owned managed target. Agency's uninstall preflight currently
examines the installed copy alone and rejects the valid two-path receipt as
unbound.

## Current state

The write-free uninstall attempt is preserved as
`Native plugin identity is not bound to the managed target`. Native inspection
proved exact plugin id `agency-preflight`, version `0.1.0`, managed source path,
installed-copy path, and the matching Agency install receipt. Recovery used
OpenClaw's native dry-run and uninstall while the gateway was stopped; the
Agency managed target and rollback evidence remain retained.

The current Agency-owned install reproduced the same write-free refusal as
operation `952ff8f6-a660-4309-ac54-191481944440`, plan digest
`a497a256064f2ececd2f27d11993cb681628e4094d2309b398c039d89ec7e2aa`.
The owned stage, install ID, bundle digest, launcher, top-level installed-copy
paths, and nested managed source/install paths all correlated; no mutation was
made and the unchanged plan was not retried. For immediate service recovery,
the stopped gateway used OpenClaw's reversible native disable. Agency remains
registered/staged but inactive; OpenClaw restarted RPC-green with Telegram and
Slack probes green and native model routing unchanged.
The operator then sent exact `reply with pong` through Telegram and received
exact `pong`. Redacted channel status records both inbound and outbound
activity, and the native transcript SHA-256 is `0420d72c...`; role-aware parsing
confirmed the exact request and assistant response without exposing identifiers.

## Approach

Teach the uninstall boundary to validate the documented OpenClaw inspect shape
as one closed provenance receipt: exact plugin identity, managed source path,
installed-copy root, source file within that root, and no conflicting path.
Keep ambiguous or partial records fail-closed.

## Dependencies

- OpenClaw native plugin inspect schema for the audited 2026.7.x line.
- Existing owned-target install-id and bundle-digest checks.

## Acceptance

- [x] Preserve both exact owned installed-copy refusal receipts.
- [x] Prove the current refusal made no mutation.
- [x] Restore ordinary OpenClaw mode through a reversible native disable.
- [x] Prove an ordinary Telegram request and exact response with Agency disabled.
- [ ] Add an expected-red for the exact installed-copy/native-source shape.
- [ ] Accept only the complete dual-path binding and retain conflicting-shape rejection.
- [ ] Run focused uninstall, registration, and host-boundary tests.
- [ ] Tracker creation remains pending separate authorization.
