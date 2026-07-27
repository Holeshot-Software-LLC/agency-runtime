---
title: "AR-183: Normalize owner-private POSIX wheel modes"
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
  - docs/roadmap/issue-AR-184-normalize-private-posix-sdist-modes.md
  - scripts/canonicalize_distributions.py
  - tests/test_canonicalize_distributions.py
supersedes: []
superseded_by: null
type: issue
epic: release
issue_id: AR-183
priority: p0
tracker_url: null
depends_on: [AR-184]
blocks:
  - AR-160
  - AR-168
  - AR-169
---

# AR-183: Normalize owner-private POSIX wheel modes

## Problem

A Linux release producer running with the security-preserving `umask 077`
causes `wheel` 0.47.0 to encode ordinary generated or copy-created members as
non-executable `0600`. The canonicalizer accepts only `0644` for POSIX ordinary
source-wheel members, so the portable producer fails before normalization even
though the input is more restrictive and the authenticated payload is valid.

## Current state

The detached `c1fee5f` WSL producer reproduced the failure before emitting an
artifact: `wheel source central record is outside the finite build allowlist`.
Independent raw-wheel inspection found 559 ordinary `0600` members, one
ordinary `0644` member, and the governed `0664` RECORD. A control build from a
`0644` checkout still emitted 267 ordinary `0600` members under `umask 077`,
binding the defect to the build tool's private-output behavior rather than Git
source modes.

After this wheel repair advanced the exact `cec7d0b` producer, the same
restrictive build exposed owner-private source-distribution modes. AR-184 owns
that distinct tar-container boundary.

## Approach

Keep the finite, platform-specific source-wheel allowlist. Add only POSIX
non-executable regular `0600` as an accepted ordinary input mode, preserve the
existing Windows and RECORD contracts, and continue normalizing every ordinary
canonical member to exact `0644`. Reject every other unreviewed mode. Re-run
the real restrictive-umask Linux producer and the merged release verifier.

## Dependencies

ADR-0074 owns byte-deterministic artifacts. AR-160, AR-168, and AR-169 own the
portable producer, canonical sdist, native-wheel split, and merged-set proof.
Tracker creation remains pending explicit outward-write authorization.

## Acceptance

- [x] POSIX `0600` ordinary source-wheel members normalize to canonical `0644`.
- [x] Windows inputs, RECORD modes, executable modes, and other unreviewed
  source modes retain their existing fail-closed contracts.
- [x] Focused canonicalization and release-package tests pass.
- [ ] A detached Linux producer under `umask 077` passes strict Twine and the
  independent portable verifier.
- [ ] Windows and Linux sdists remain byte-identical and the merged three-file
  release set passes independent verification.

## Implementation evidence

The finite source-wheel allowlist now accepts only POSIX ordinary regular
`0600` in addition to its existing exact modes. Canonical output remains exact
ordinary `0644` and RECORD `0664`. Regressions prove byte convergence between
otherwise identical `0600` and `0644` inputs and reject Windows `0600`, altered
RECORD modes, executable/setuid modes, special file types, and nonzero low
attribute bits. The four-file canonicalizer/build/verifier/release package
passed 383 tests; after independent review expanded the boundary matrix, the
canonicalizer file passed 83 tests. Ruff, formatting, documentation, and diff
checks pass. The real Linux producer and merged-set proof remain pending.
