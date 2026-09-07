---
title: "AR-168: Rebuild the canonical sdist source manifest"
status: in_progress
category: roadmap
created: 2026-07-27
updated: 2026-09-07
tags: [release, packaging, reproducibility, metadata]
related:
  - docs/roadmap/acceptance/evidence/AR-168-source-manifest-20260907.md
  - docs/roadmap/issue-AR-404-evidence-led-backlog-completion.md
  - docs/decisions/0219-retire-removed-helper-release-obligations.md
  - docs/roadmap/issue-AR-107-build-release-artifacts-from-canonical-git-blobs.md
  - docs/roadmap/issue-AR-160-publish-platform-honest-native-release-artifacts.md
  - docs/roadmap/issue-AR-183-normalize-private-posix-wheel-modes.md
  - docs/roadmap/issue-AR-184-normalize-private-posix-sdist-modes.md
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
depends_on: [AR-107, AR-183, AR-184]
blocks: [AR-160]
---

# AR-168: Rebuild the canonical sdist source manifest

## Problem

Historically, the pinned build backend automatically classified the Windows native
license and notice files as distribution licenses while `MANIFEST.in` also
includes them as reviewed package data. The resulting source archive contains
each file once, but its generated `agency_runtime.egg-info/SOURCES.txt` lists
the three paths twice. The independent distribution verifier correctly rejects
the duplicate generated manifest, so a clean producer cannot pass the release
gate even though the source members themselves are unique.

## Current state

The generic manifest repair is present and still relevant. The canonicalizer
rebuilds from validated archive members; the independent verifier separately
requires exact membership and bytes. No implementation change is needed.
September 7's 308 focused tests pass, with one actual native-Windows case
deselected for the owner. Portable synthetic platform cases are not Windows proof.

Clean 6363a788132b8419c69f26a1dd802534e57782cd produces a Linux portable
wheel/source pair that passes independent verification and strict Twine.
The source has 2,258 files and 2,256 distinct manifest rows: root PKG-INFO and
setup.cfg excluded, self row present, no CR or trailing newline. Exact hashes
and reproducible commands are in the [receipt](acceptance/evidence/AR-168-source-manifest-20260907.md).

The original five acceptance criteria and states remain unchanged. The missing
same-candidate native Windows/Linux byte comparison remains owner evidence,
also required by AR-160/ADR-0219, not a reproduced Linux manifest defect.

### Historical failure, not current state

The July detached Windows build passed strict descriptions but failed generated
manifest verification: 1,307 rows versus 1,304 distinct paths. Duplicates were
the C++/WinRT license, Microsoft STL license and notice. ADR-0219 retains generic
artifact proof but forbids restoring those removed helper obligations.

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
metadata verification. This unmapped record retains its existing pre-tracker
exemption; no duplicate tracker is created by reconciliation.

## Remaining bounded package

The owner builds on native Windows at the same reviewed commit as Linux (or
regenerates both at one new clean commit). Independently verify both source
archives against that commit and compare their complete bytes. Preserve producer
identity and hashes; synthetic Windows fixtures or retagged Linux artifacts do
not satisfy the gate. Feed the pair into AR-160's release-set verification.
Only then collect all isolated acceptance verdicts before marking this done.

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
