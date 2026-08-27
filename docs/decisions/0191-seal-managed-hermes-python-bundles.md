---
title: "Seal managed Hermes Python cache namespaces"
status: accepted
category: decisions
created: 2026-08-27
updated: 2026-08-27
tags: [hermes, installation, python, filesystem, security, linux]
related:
  - docs/roadmap/issue-AR-297-complete-unattended-container-bootstrap.md
  - docs/roadmap/issue-AR-328-seal-hermes-install-tree.md
  - docs/roadmap/handoffs/issue-AR-297.md
  - CHANGELOG.md
  - docs/THREAT_MODEL.md
  - agency_runtime/core/installer_contracts.py
  - agency_runtime/core/installer_filesystem.py
  - agency_runtime/core/installer_payload_manifests.py
  - tests/test_installer_coverage_complete_filesystem_native.py
  - docs/worklog/README.md
supersedes: []
superseded_by: null
id: ADR-0191
type: decision
deciders: [maintainers]
---

# ADR-0191: Seal managed Hermes Python cache namespaces

## Context

Hermes imports Agency's generated native plugin as a Python package. Python's
ordinary source loader attempts to materialize a version-specific bytecode
cache before executing that package. The managed ownership manifest lists only
canonical generated inputs, so the new cache correctly fails strict exact-tree
validation. Removing it after each load would make validation timing-dependent;
allowlisting arbitrary bytecode would let an executable derivative enter the
trusted plugin tree without being built or independently verified.

## Decision

On POSIX, the installer includes one ownership-manifested marker inside the
Hermes bundle's `__pycache__` directory. It writes the complete bundle inside
its exclusive owner-private staging tree, then sets only that cache directory
to mode 0500 and its marker to mode 0400 before the atomic rename into the
native plugin location. The manifest records
`python-bytecode-cache-denied-v1`, and strict ownership validation enforces
those exact guard modes. An exact-content Hermes bundle whose guard is not
sealed is not idempotently accepted; the installer replaces it through the
existing backup transaction.

If a failure occurs after sealing but before the final rename, the installer
restores private writable modes only on that still-bound cache guard before
quarantined cleanup. The plugin root remains mode 0700 and transactionally
movable, so install backup, rollback, and ownership-bound uninstall retain their
existing rename contract. Codex, Claude, OpenClaw, ZCode, foreign harness
policy, and host service definitions remain unchanged. Windows keeps its
existing private-DACL behavior and requires separate platform evidence; this
decision supplies the Linux/POSIX contract.

## Consequences

Normal Hermes imports remain readable and executable but cannot add files to
`__pycache__`. Exact validation therefore survives ordinary gateway and service
restarts. A deliberate owner guard-mode change is visible as policy drift and
forces a fresh transactional install.

Future Hermes integrations that legitimately need mutable state must place it
outside the managed plugin tree and bind it separately. POSIX rollback can
still atomically rename sealed directories because mutation authority belongs
to the private parent; legacy retained bundles remain readable for recovery.

## Alternatives

Ignoring `__pycache__` was rejected because unmanifested executable files would
gain admission. Deleting caches after startup was rejected because proof would
depend on timing and fail again after restart. Shipping a precompiled `.pyc`
was rejected because its tag and contents depend on the host interpreter.
Sealing the entire plugin root was rejected because it breaks the existing
cross-parent atomic rename used by upgrade and uninstall. Changing the foreign
systemd environment or Hermes policy was rejected because the installer owns a
narrower, deterministic cache namespace.
