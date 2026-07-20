---
title: Verify the pinned backend's exact source-manifest order
status: active
category: worklog
created: 2026-07-20
updated: 2026-07-20
tags: [release, reproducibility, setuptools, verification]
related:
  - docs/roadmap/issue-AR-107-build-release-artifacts-from-canonical-git-blobs.md
  - docs/decisions/0074-build-byte-deterministic-release-artifacts.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: worklog
commit: 3515d4e1df83b5a019e3c99cff6ef6b9bb99ca17
short: 3515d4e
date: 2026-07-20
pr: https://github.com/Holeshot-Software-LLC/agency-runtime/pull/111
related_issues:
  - docs/roadmap/issue-AR-107-build-release-artifacts-from-canonical-git-blobs.md
---

# Worklog detail: Verify the pinned backend's exact source-manifest order

## Purpose

Repair the independent distribution verifier after the first exact clean-commit
Windows build showed that `setuptools` orders `SOURCES.txt` by parent directory
and basename rather than by one global path-string sort.

## Approach

Derive the expected member set independently from the source archive, then
order it with a platform-neutral `(parent, basename)` key. Continue to require
exact membership, LF bytes, no final newline, and no duplicates. The verifier
does not import or execute `setuptools` code.

## Challenges encountered

The prior synthetic fixture did not contain paths that distinguish global
sorting from the backend's order. A real 993-entry manifest exposed the gap:
root files precede package directories, and files in a directory precede files
in its subdirectories. The new regression contains all three cases.

## Decisions and alternatives

Do not loosen the verifier to accept arbitrary ordering and do not import the
build backend as verification authority. Reproduce only the pinned backend's
small deterministic ordering contract.

## Verification

- The exact clean Windows artifact's 993-entry `SOURCES.txt` now matches the
  independent expected payload byte-for-byte.
- Verifier suite: 326 passed; 1,506 statements and 614 branches at 100.00%.
- Ruff, formatting, documentation, worklog, and whitespace gates passed.

## Follow-ups

Rebuild the next exact ledger commit on Windows and WSL, then require hosted
parity and merge-commit artifact proof before completing
[AR-107](../roadmap/issue-AR-107-build-release-artifacts-from-canonical-git-blobs.md).
