---
title: "AR-168: Rebuild the canonical sdist source manifest"
status: in_progress
category: roadmap
created: 2026-07-27
updated: 2026-07-27
tags: [release, packaging, reproducibility, metadata]
related:
  - docs/roadmap/issue-AR-107-build-release-artifacts-from-canonical-git-blobs.md
  - docs/roadmap/issue-AR-160-publish-platform-honest-native-release-artifacts.md
  - docs/roadmap/issue-AR-183-normalize-private-posix-wheel-modes.md
  - docs/decisions/0074-build-byte-deterministic-release-artifacts.md
  - scripts/canonicalize_distributions.py
  - scripts/verify_distribution.py
  - tests/test_canonicalize_distributions.py
supersedes: []
superseded_by: null
type: issue
epic: release
issue_id: AR-168
priority: p0
tracker_url: null
depends_on: [AR-107, AR-183]
blocks: [AR-160]
---

# AR-168: Rebuild the canonical sdist source manifest

## Problem

The pinned build backend automatically classifies the packaged Windows native
license and notice files as distribution licenses while `MANIFEST.in` also
includes them as reviewed package data. The resulting source archive contains
each file once, but its generated `agency_runtime.egg-info/SOURCES.txt` lists
the three paths twice. The independent distribution verifier correctly rejects
the duplicate generated manifest, so a clean producer cannot pass the release
gate even though the source members themselves are unique.

## Current state

A detached clean Windows build emits the expected wheel/source pair and passes
strict package-description checks. Independent content verification stops on
the duplicated generated source manifest. Exact diagnostic parsing found 1,307
rows but only 1,304 distinct portable paths; the three duplicates are the
reviewed C++/WinRT license, Microsoft STL license, and Microsoft STL notice.

## Approach

Treat `SOURCES.txt` as generated container metadata, like wheel `RECORD`.
Rebuild it from the already bounded, unique, safe source-tar member set after
topology validation. Exclude only the backend-generated root `PKG-INFO` and
`setup.cfg` entries, retain the manifest's self entry, use the independently
specified parent/name backend order, encode UTF-8 with canonical LF separators,
and omit a trailing newline. The independent verifier continues to derive the
same expectation separately from final archive contents.

## Dependencies

AR-107 and ADR-0074 own deterministic archive canonicalization and independent
verification. AR-160 cannot accept a producer pair that fails generated-
metadata verification. Creating the same-repository tracker issue remains
pending outward-write authorization.

## Acceptance

- [x] Canonicalization derives `SOURCES.txt` from unique safe archive members,
  not from backend-provided rows.
- [x] Missing, duplicate, or extra backend rows cannot survive into the
  canonical source distribution.
- [x] The manifest uses exact backend-order UTF-8/LF bytes without a trailing
  newline and retains its own member row.
- [ ] Detached clean Windows and Linux source distributions are byte-identical
  and independently pass the full generated-metadata contract.
- [ ] Proportionate formatting, tests, documentation validation, and clean-tree
  checks pass.
