---
title: "AR-328: Seal the managed Hermes bytecode cache"
status: in_progress
category: roadmap
created: 2026-08-27
updated: 2026-08-27
tags: [bug, hermes, installation, filesystem, security, linux]
related:
  - docs/roadmap/issue-AR-297-complete-unattended-container-bootstrap.md
  - docs/roadmap/handoffs/issue-AR-297.md
  - docs/decisions/0191-seal-managed-hermes-python-bundles.md
  - CHANGELOG.md
  - docs/THREAT_MODEL.md
  - agency_runtime/core/installer_contracts.py
  - agency_runtime/core/installer_filesystem.py
  - agency_runtime/core/installer_payload_manifests.py
  - tests/test_installer_coverage_complete_filesystem_native.py
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: host-integrations
issue_id: AR-328
priority: p0
tracker_url: null
depends_on: []
blocks: [AR-297]
---

# AR-328: Seal the managed Hermes bytecode cache

## Problem

An ordinary Hermes plugin load imports Agency's generated `__init__.py` and
creates `__pycache__/__init__.cpython-*.pyc` inside the ownership-manifested
plugin directory. Strict install-tree validation then rejects the unexpected
executable artifact even though the source bundle and manifest remain intact.
A one-time cache deletion would pass only until the next normal service start.

## Current state

- The exact AR-297 Linux-host install initially contains only its manifested
  files, but an ordinary Hermes service load adds one unmanifested bytecode
  cache below `~/.hermes-nexus/plugins/agency-preflight`.
- The managed target root is owner-private and must remain transactionally
  movable for upgrades, rollback, and uninstall.
- Regression receipt `751276ea...e3a` exits 1 before the repair because the
  installed Hermes bundle has no sealed cache namespace.
- No foreign Hermes policy, systemd unit, model route, or credential is changed
  by the repair. Tracker creation remains prohibited by AR-297.

## Approach

Generate one manifested marker inside Hermes' `__pycache__` namespace. After
writing the exclusive private staging tree, set that directory to mode 0500 and
its marker to mode 0400 before atomic rename. Record the policy in the manifest,
require it during strict ownership validation, and treat an exact bundle with
an unsealed guard as changed so reinstall replaces it. If the pre-rename
transaction fails, restore writable modes only on the guarded staging namespace
before bounded cleanup. Leave the movable target root and every other native
host bundle contract unchanged.

## Dependencies

- AR-297 owns the exact rebuilt artifact, production-container, Linux-host,
  ordinary-process, and teardown evidence.
- ADR-0191 governs the POSIX Hermes bundle-sealing contract.
- Tracker creation requires separate outward-write authorization.

## Acceptance

- [x] A regression reproduces the normal-umask writable Hermes staging result.
- [x] A generated POSIX Hermes bundle contains an owner-readonly bytecode-cache
      guard, imports successfully, and creates no unmanifested bytecode.
- [x] Strict ownership rejects guard-mode drift, and reinstall replaces an
      exact unsealed guard rather than reporting it unchanged.
- [x] Focused warning-strict installer, rollback, and uninstall tests pass.
- [x] Exact rebuilt artifacts and production images pass independent checks.
- [x] A fresh host install survives Hermes restart and strict exact-tree
      validation with no unmanifested cache.
- [ ] A same-repository tracker issue is created and linked after explicit
      authorization.

## Verification

Owner-private source receipts remain under
`~/.agency-runtime/evidence/ar297-go-e17e5221/`. The regression-first failure
exits 1 at stdout `751276ea...e3a`; the final broader installer, rollback,
authority, and uninstall set passes 359 tests with 2 skips at
`981fbbc8...ddd0`. Candidate `e0b0b25c` artifacts are retained under
`~/.agency-runtime/evidence/ar297-go-e0b0b25c/`: canonical build, strict Twine,
independent distribution verification, manifest, and six final image builds
exit 0. Wheel/sdist hashes are `75d63ff9...3762`/`2b1ae7ec...79d9`; final image
verification exits 0 at `07f372e3...eb9a`. R1's exit 1 is retained: it caught
an incorrect Node 22 OpenClaw rebuild before the established Node 24.15 pin was
restored. Final UID-10000 Hermes install `4d04f360...02d8`, native doctor, and
the post-load strict-tree receipt `d7bc15f0...d8f8` exit 0. The latter binds
image `3a4cac26...1bf`, policy `python-bytecode-cache-denied-v1`, target/guard/
marker modes 0700/0500/0400, no `.pyc`, and exact validation. Only the
authorization-prohibited tracker mapping remains open.
