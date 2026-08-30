---
title: "AR-184: Normalize owner-private POSIX sdist modes"
status: in_progress
category: roadmap
created: 2026-07-27
updated: 2026-07-27
tags: [release, packaging, linux, reproducibility, security]
related:
  - docs/decisions/0074-build-byte-deterministic-release-artifacts.md
  - docs/roadmap/issue-AR-160-publish-platform-honest-native-release-artifacts.md
  - docs/roadmap/issue-AR-168-rebuild-canonical-sdist-source-manifest.md
  - docs/roadmap/issue-AR-169-exclude-native-pe-from-portable-wheel.md
  - docs/roadmap/issue-AR-183-normalize-private-posix-wheel-modes.md
  - scripts/canonicalize_distributions.py
  - tests/test_canonicalize_distributions.py
supersedes: []
superseded_by: null
type: issue
epic: release
issue_id: AR-184
priority: p0
tracker_url: null
depends_on: []
blocks:
  - AR-183
  - AR-160
  - AR-168
  - AR-169
---

# AR-184: Normalize owner-private POSIX sdist modes

## Problem

After AR-183 advanced the exact Linux producer past source-wheel validation, a
build running under the required `umask 077` failed on the raw source
distribution. Setuptools 83.0.0 emitted ordinary regular files as owner-private
`0600` and directories as owner-private `0700`; the canonicalizer accepted only
the public POSIX projections and Windows projections.

The rejected inputs are safer than public modes and contain no executable
regular file, but the incomplete finite allowlist prevented a portable artifact
from being published.

## Current state

The detached exact `cec7d0b` WSL producer failed closed with
`sdist source directory header is outside the build allowlist` and left the
destination absent. Independent raw inspection counted 1,353 ordinary files at
`0600`, two generated metadata files at `0644`, and 40 directories at `0700`.
No other mode or member type was present.

## Approach

Add only exact owner-private ordinary file `0600` and directory `0700` to the
raw sdist allowlists. Preserve the separate governed Windows executable
exception, reject every other unreviewed permission or member type, and keep
canonical output fixed at ordinary file `0644` and directory `0755`. Prove byte
convergence with the existing public POSIX projections before rerunning the real
producer and merged release verifier.

## Dependencies

ADR-0074 owns deterministic container normalization. AR-160, AR-168, and AR-169
own the paired producers, canonical sdist, portable wheel, and merged-set proof.
Tracker creation remains pending explicit outward-write authorization.

## Acceptance

- [x] Raw ordinary sdist files at exact `0600` normalize to canonical `0644`.
- [x] Raw sdist directories at exact `0700` normalize to canonical `0755`.
- [x] Private and public POSIX source modes converge to byte-identical output.
- [x] Executable, special-file, and other unreviewed modes remain fail closed.
- [ ] A detached Linux producer under `umask 077` passes strict Twine and the
  independent portable verifier.
- [ ] Windows and Linux sdists are byte-identical and the merged three-file
  release set passes independent verification.

## Implementation evidence

The exact producer failure and raw mode census are preserved outside the
repository under an owner-private proof root. The focused canonicalizer suite
passes with private/public byte convergence and an exhaustive exact-mode
contract across all permission-bit combinations. The four-file canonicalizer,
builder, verifier, and release-package suite passes 411 tests. Independent
security review found no Critical, High, or Medium defect. Cross-platform
producer and merged-set evidence will be recorded after the repair is committed.
