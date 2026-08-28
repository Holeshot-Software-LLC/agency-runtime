---
title: "AR-329: Freeze the Codex inspector bootstrap as a persistent input"
status: in_progress
category: roadmap
created: 2026-08-28
updated: 2026-08-28
tags: [bug, codex, hooks, activation, security, linux]
related:
  - docs/roadmap/issue-AR-297-complete-unattended-container-bootstrap.md
  - docs/roadmap/handoffs/issue-AR-297.md
  - docs/decisions/0177-make-local-verification-private-by-construction.md
  - agency_runtime/core/codex_hook_trust.py
  - agency_runtime/core/process_argv.py
  - tests/test_codex_hook_trust.py
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: host-integrations
issue_id: AR-329
priority: p0
tracker_url: null
depends_on: []
blocks: [AR-297]
---

# AR-329: Freeze the Codex inspector bootstrap as a persistent input

## Problem

Current-profile Codex activation verification fails before model invocation
even after the operator settles trust for all eight Agency hooks. The isolated
inspector launches a private Python bootstrap as an interpreter input, but
freezes that bootstrap with the direct-executable guard. The sealed private
projection intentionally installs Python source without an execute bit, so the
guard rejects it and the verifier reports `inspection_failed` with zero hooks.

## Current state

- Codex 0.149.1 reports all eight exact Agency hooks enabled and trusted when
  the inspector worker is launched through the same private projection without
  the incorrect direct-executable classification.
- The private bootstrap is owner-controlled, mode 0400, manifest-verified, and
  passed to an owner-protected Python interpreter with `-I -S`.
- The verifier remains fail-closed and does not invoke a model when the trust
  report cannot be authenticated.
- Tracker creation is prohibited by the active AR-297 task.

## Approach

Freeze the worker interpreter and bootstrap with the existing persistent
artifact guard. That guard still requires argv[0] to be executable and binds
both artifacts by path, ownership, mode, metadata, and content hash, while
correctly treating the bootstrap as a non-executable Python input. Keep the
published-projection requirement, repository exclusion, isolated interpreter,
bounded protocol, and strict eight-hook trust predicate unchanged.

## Dependencies

- AR-297 owns the exact Linux-host install, ordinary-process, Store,
  authenticated dashboard, and final GO evidence.
- ADR-0177 governs owner-private verification artifacts.
- Tracker creation requires separate outward-write authorization.

## Acceptance

- [x] A regression proves a mode-0400 published bootstrap receives persistent
      artifact identities and can return a trusted report.
- [x] Focused Codex hook and activation tests pass warning-strict.
- [ ] An exact built and installed runtime reports eight of eight Codex hooks
      trusted without bypass and persists a fresh current-profile attestation.
- [ ] Every named repository gate passes for the exact candidate.
- [ ] A same-repository tracker issue is created and linked after explicit
      authorization.

## Verification

Substantive repair `aead84d0c89d13002d67d0a25d6978c8e6fca05e` and ledger
`b25951bae8091b9906ffad628ac85e64afb4bc62` pass 127 focused warning-strict
Codex trust and activation tests. The exact portable wheel and source archive
hash to `5f2c9b5d...4e33` and `24875bca...eff7`; canonical build, strict Twine,
and independent distribution verification exit 0. Host refresh receipt
`10c50ca...82fb` installs the four exact bundles and dashboard. The corrected
inspector distinguishes the post-refresh operator state truthfully: all eight
hooks are present and `modified`, so a fresh attended trust grant is required
before the no-bypass live verifier can run.
