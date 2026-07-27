---
title: "AR-167: Normalize Windows release-source modes"
status: in_progress
category: roadmap
created: 2026-07-27
updated: 2026-07-27
tags: [release, packaging, windows, reproducibility]
related:
  - docs/roadmap/issue-AR-107-build-release-artifacts-from-canonical-git-blobs.md
  - docs/roadmap/issue-AR-160-publish-platform-honest-native-release-artifacts.md
  - docs/decisions/0074-build-byte-deterministic-release-artifacts.md
  - scripts/build_distributions.py
  - tests/test_build_distributions.py
supersedes: []
superseded_by: null
type: issue
epic: release
issue_id: AR-167
priority: p0
tracker_url: null
depends_on: [AR-107]
blocks: [AR-160]
---

# AR-167: Normalize Windows release-source modes

## Problem

The canonical distribution builder requires every reviewed Git source entry to
be a non-executable `100644` blob and then verifies the materialized source tree
before invoking the build backend. On Windows, CPython reports a file ending in
`.exe` as mode `0777` even after `chmod(0644)` because Windows has no POSIX
execute bit. The verifier expected every writable Windows file to report mode
`0666`, so a clean build of the reviewed operator-presence executable failed
before artifact creation despite the authenticated Git entry being `100644`.

## Current state

The failure was reproduced from a detached clean checkout of the audited commit
while preparing fresh Windows release artifacts. The Git manifest reports the
helper as `100644`; the same file's Windows `os.lstat` projection is `0777`.
This is a release-blocking portability defect in the physical-tree check, not a
change to the reviewed Git-mode contract.

## Approach

Keep the authenticated Git manifest requirement unchanged. Normalize only the
mode that CPython can faithfully report after canonical materialization: POSIX
files remain exactly `0644`; ordinary writable Windows files remain `0666`; and
Windows `.exe` paths must report exactly `0777`. Continue rejecting every other
mode, link, reparse point, multi-link file, unstable identity, size change, and
blob-hash mismatch.

## Dependencies

AR-107 and ADR-0074 own the canonical Git-blob build boundary. AR-160 requires a
successful clean Windows producer before the platform-paired release set can be
accepted. Creating the same-repository tracker issue remains pending outward-
write authorization.

## Acceptance

- [x] Authenticated release entries still must be non-executable `100644` Git
  blobs before any source bytes are materialized.
- [x] The physical-tree verifier accounts only for CPython's Windows `.exe`
  mode projection and preserves exact checks for all other platforms and files.
- [x] Unit tests cover lowercase and uppercase `.exe`, ordinary Windows files,
  and POSIX behavior.
- [ ] A detached clean Windows build of the exact reviewed commit emits and
  independently verifies its Windows wheel and source distribution.
- [ ] Proportionate formatting, tests, documentation validation, and clean-tree
  checks pass.
