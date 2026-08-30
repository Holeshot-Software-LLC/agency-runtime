---
title: "AR-65: Reject cross-account-writable executable namespaces"
status: done
category: roadmap
created: 2026-07-16
updated: 2026-07-16
tags: [security, processes, executables, delegation, portability, testing]
related:
  - docs/decisions/0038-refuse-executable-git-configuration-during-delegation.md
  - docs/decisions/0055-freeze-executable-identity-before-launch.md
  - docs/roadmap/issue-AR-60-frozen-executable-identity.md
  - docs/THREAT_MODEL.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: security
issue_id: AR-65
priority: p0
tracker_url: "https://github.com/Holeshot-Software-LLC/agency-runtime/issues/66"
depends_on: [AR-60]
blocks: []
---

# AR-65: Reject cross-account-writable executable namespaces

## Problem

Absolute-only discovery and frozen file identities do not make an executable
trustworthy when another operating-system account can replace its parent
namespace. A hostile absolute `PATH` entry such as a broadly writable
`/tmp/agency-bin` can supply a valid-looking executable and replace its name
between identity validation and the operating system's executable open. Linux
dashboard lifecycle commands also passed a bare service-manager name through a
direct subprocess path that bypassed executable freezing.

## Current state

Every launch-critical executable, interpreter, wrapper, and service manager
passes canonical identity freezing plus an explicit parent-chain trust boundary
at freeze and final revalidation. Persistent host and dashboard manifests add
content-bound interpreter/bootstrap identity, and native inspection or
lifecycle refuses drifted launchers.

## Approach

On POSIX, accept only real directory chains owned by root or the effective user,
honor safe sticky shared ancestors, reject writable final parents and default
ACLs, and preserve root-owned system paths. On Windows, require the existing
access-aware DACL probe to prove that untrusted principals cannot mutate each
namespace. Recheck the namespace immediately before launch alongside the frozen
artifact identity and preserve injectable test-runner seams without treating
them as production proof.

## Dependencies

AR-60 and ADR-0055 define canonical artifact freezing and final identity
revalidation. This correction closes the remaining cross-account namespace gap
without claiming protection from same-account or administrator races.

## Acceptance

- [x] Executables beneath a cross-account-writable final parent fail closed.
- [x] Non-sticky writable ancestors and unsafe POSIX default ACLs fail closed.
- [x] Root-owned system directories and private current-user directories remain usable.
- [x] Windows DACL simulation proves unsafe parent namespaces are rejected.
- [x] Namespace trust is checked during freeze and immediately before process creation.
- [x] Dashboard service-manager commands use the same trusted launch boundary.
- [x] No child process starts after namespace trust fails.
- [x] Focused, cross-platform, full-suite, exact-coverage, and installed smoke gates pass.
