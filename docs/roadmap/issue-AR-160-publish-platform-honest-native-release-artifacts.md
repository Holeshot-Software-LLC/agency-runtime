---
title: "AR-160: Publish platform-honest native release artifacts"
status: in_progress
category: roadmap
created: 2026-07-27
updated: 2026-07-27
tags: [release, packaging, windows, portability, reproducibility]
related:
  - docs/roadmap/issue-AR-107-build-release-artifacts-from-canonical-git-blobs.md
  - docs/roadmap/issue-AR-143-require-operator-presence-for-controls.md
  - docs/roadmap/issue-AR-161-sign-and-license-windows-operator-presence-delivery.md
  - docs/roadmap/issue-AR-167-normalize-windows-release-source-modes.md
  - docs/roadmap/issue-AR-168-rebuild-canonical-sdist-source-manifest.md
  - docs/roadmap/issue-AR-169-exclude-native-pe-from-portable-wheel.md
  - docs/roadmap/issue-AR-181-bound-all-host-smoke-launcher-preparation.md
  - docs/roadmap/issue-AR-183-normalize-private-posix-wheel-modes.md
  - docs/roadmap/issue-AR-184-normalize-private-posix-sdist-modes.md
  - docs/decisions/0074-build-byte-deterministic-release-artifacts.md
  - docs/decisions/0098-pair-portable-and-win-amd64-wheels.md
  - docs/RELEASE_CHECKLIST.md
  - docs/THREAT_MODEL.md
  - scripts/verify_distribution.py
supersedes: []
superseded_by: null
type: issue
epic: release
issue_id: AR-160
priority: p0
tracker_url: null
depends_on: [AR-107, AR-167, AR-168, AR-169, AR-181, AR-183, AR-184]
blocks: [AR-143, AR-161]
---

# AR-160: Publish platform-honest native release artifacts

## Problem

The package contains an x86-64 Windows PE executable used by the first operator-
presence implementation. Before this work package, its only wheel advertised
`py3-none-any`, claiming complete compatibility with every platform. A native
executable invoked as a subprocess is itself a valid reason for a platform-
specific tag, even though it is not a Python extension module. Publishing that
former artifact would have overstated compatibility and installed unusable
Windows-only bytes on Linux, Windows ARM64, and other unsupported systems.

## Current state

The source now derives one immutable wheel profile from the actual build host.
Supported Windows x64 produces `py3-none-win_amd64` with
`Root-Is-Purelib: false` and the reviewed PE. Linux and every other host produce
`py3-none-any` with `Root-Is-Purelib: true` and exclude only that exact PE;
portable audit material—the native source, provenance, and local notices—stays
shared. A source build uses the same host-derived rule.

Each producer builds and verifies one host pair: one profile-specific wheel plus
one canonical source distribution. Exact candidate `29da6eca` now has clean
Windows and WSL/Linux producer evidence. The two source distributions are
byte-identical, the assembled portable wheel, Windows wheel, and one source
distribution pass strict Twine metadata checks, and the independent
three-artifact `release` verifier passes. Fresh wheel and source installs pass
on Windows Python 3.10 and Linux Python 3.12; the portable wheel scan found no
executable or PE payload. Current hosted cross-OS proof is still pending because
repository Actions billing is disabled; no publication claim follows from
local evidence alone.

## Approach

Complete and prove ADR-0098 as one same-version release set with a portable
`py3-none-any` wheel and a `py3-none-win_amd64` wheel. The portable wheel excludes
only the Windows PE and continues to fail that operation closed; it retains the
reviewable source, provenance, and license/notice files. The Windows wheel adds
the exact reviewed PE. Keep Python packages, version, dependencies, entry
points, and core metadata equivalent apart from that single executable and the
finite wheel tag, installation-root, and `RECORD` differences it requires.

Each producer continues to build exactly one wheel/source pair from canonical
Git blobs. Preserve deterministic equality for the two producer source
distributions and exact equality for every shared wheel payload. The merge gate
assembles exactly three artifacts and verifies their complete relationship;
producer jobs do not claim to build the other host's wheel. Compare a Windows
delivery wheel only after its exact signed payload has been fixed for the
release. Reject a missing variant, duplicate or cross-contaminated PE,
incorrect filename/WHEEL/root tag, metadata drift, non-identical source
distributions, shared-payload drift, or artifacts from different commits.

## Dependencies

AR-107 and ADR-0074 provide the canonical Git-blob, deterministic-container,
and independent-verification foundation. AR-161 separately owns publisher
identity, signed delivery, and compiler/runtime/SDK legal disposition; an
honest platform tag alone does not make the Windows payload production-ready.

Creating the same-repository tracker item remains pending authorization.

## Acceptance

- [x] One reviewed merged release set contains exactly one portable
  `py3-none-any` wheel, one `py3-none-win_amd64` wheel, and the explicitly
  governed source-distribution artifact.
- [x] The portable wheel retains the native source, provenance, and local
  notices but contains no PE; the Windows wheel contains the same shared audit
  material plus exactly the reviewed executable.
- [x] Both wheels share version, dependencies, entry points, Python package
  behavior, and core metadata except for a finite reviewed platform delta.
- [x] Filename tags and WHEEL metadata agree; the portable wheel uses
  `Root-Is-Purelib: true`, the Windows wheel uses `Root-Is-Purelib: false`, and
  neither value is misrepresented as a separate trust or signature claim.
- [x] A fresh Linux install selects the portable wheel and keeps native
  operator presence unavailable; a fresh supported Windows x64 install selects
  the `win_amd64` wheel and finds only the pinned delivery payload.
- [x] Windows ARM64 and every other unsupported environment cannot install or
  invoke the x64 helper through an inaccurately compatible artifact.
- [x] Source-distribution build behavior derives the same immutable profile
  from the actual host, is deterministic and tested, and cannot emit a
  universal wheel carrying the Windows executable.
- [x] The independent verifier rejects missing pairs, duplicate variants,
  cross-contamination, tag/root metadata mismatch, version or dependency drift,
  cross-commit inputs, and unapproved native bytes.
- [x] Linux and Windows producers each emit one wheel/source pair. The merge
  gate proves byte-identical source distributions and shared wheel payloads,
  then assembles and verifies the exact three-artifact release set.
- [ ] Fresh isolated wheel and source-distribution smoke, packaging, docs,
  warning-strict tests, and hosted Windows/Linux artifact gates pass.
