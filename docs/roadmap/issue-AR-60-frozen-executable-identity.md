---
title: "AR-60: Freeze executable identity from discovery through launch"
status: done
category: roadmap
created: 2026-07-16
updated: 2026-07-16
tags: [security, processes, executables, delegation, portability]
related:
  - docs/decisions/0055-freeze-executable-identity-before-launch.md
  - docs/roadmap/issue-AR-65-reject-cross-account-executable-namespaces.md
  - docs/decisions/0038-refuse-executable-git-configuration-during-delegation.md
  - docs/THREAT_MODEL.md
  - docs/TROUBLESHOOTING.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: security
issue_id: AR-60
priority: p0
tracker_url: "https://github.com/Holeshot-Software-LLC/agency-runtime/issues/61"
depends_on: [AR-35]
blocks: [AR-61, AR-65]
---

# AR-60: Freeze executable identity from discovery through launch

## Problem

Finding a command by name and launching it later can cross two attacker-
controlled boundaries. Empty, relative, or current-directory `PATH` entries
can select repository content, and a selected executable or wrapper can be
replaced after validation but before process creation.

## Current state

Transient launch preparation accepts only absolute explicit paths or results
from absolute `PATH` entries. It rejects Windows links and reparse points,
non-regular files, wrong Windows launcher kinds, and artifacts whose canonical
target is inside the delegated repository. A transient POSIX launcher symlink
is canonicalized before execution. Persistent host and dashboard launchers
preserve environment-managed lexical POSIX interpreter spelling while their
manifest freezes the link target, resolved interpreter, package bootstrap,
metadata, ownership, namespace, and content. Drift fails inspection and blocks
lifecycle execution until reinstall.

## Approach

Centralize executable discovery and launch preparation in one typed argv
contract. Preserve argument-array execution without a shell. Capture the
canonical path, device, inode, type/mode, size, modification time, and Windows
file attributes for the executable and any required wrapper artifact. Resolve
Git and native system utilities through trusted absolute paths. Refuse launch
if any frozen field changes or a required identity cannot be proven.

## Dependencies

AR-16 established portable delegated execution, and AR-35 established trusted
Windows system-command resolution. ADR-0055 extends those boundaries to every
launch-critical artifact.

## Acceptance

- [x] Empty, dot, relative, and current-directory `PATH` entries are ignored.
- [x] Relative explicit executable paths are rejected.
- [x] Windows links/reparse points, non-files, and repository-local canonical targets fail closed.
- [x] Transient POSIX launcher symlinks are canonicalized to their executable target.
- [x] Persistent POSIX launcher symlinks retain lexical argv while the link and resolved target are frozen.
- [x] Windows launch executables use an allowlisted native suffix.
- [x] Wrapper and interpreter artifacts are frozen with the native executable.
- [x] Every frozen identity is revalidated immediately before process creation.
- [x] Replacement or mutation after preparation prevents launch.
- [x] Persistent host/dashboard manifests bind interpreter and package bootstrap content identities.
- [x] Inspection, registration, start, and restart reject persistent launcher drift.
