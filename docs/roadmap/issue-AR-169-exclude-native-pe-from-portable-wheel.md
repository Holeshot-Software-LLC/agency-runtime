---
title: "AR-169: Exclude the native PE from portable wheels"
status: wont_do
category: roadmap
created: 2026-07-27
updated: 2026-09-05
tags: [release, packaging, portability, windows, wheel]
related:
  - docs/decisions/0219-retire-removed-helper-release-obligations.md
  - docs/roadmap/issue-AR-197-remove-agency-owned-windows-hello.md
  - docs/roadmap/AR-404-backlog-dispositions-20260905.md
  - docs/roadmap/issue-AR-107-build-release-artifacts-from-canonical-git-blobs.md
  - docs/roadmap/issue-AR-160-publish-platform-honest-native-release-artifacts.md
  - docs/roadmap/issue-AR-183-normalize-private-posix-wheel-modes.md
  - docs/roadmap/issue-AR-184-normalize-private-posix-sdist-modes.md
  - docs/decisions/0098-pair-portable-and-win-amd64-wheels.md
  - scripts/platform_wheel.py
  - scripts/verify_distribution.py
  - tests/test_platform_wheel.py
supersedes: []
superseded_by: docs/roadmap/issue-AR-197-remove-agency-owned-windows-hello.md
type: issue
epic: release
issue_id: AR-169
priority: p0
tracker_url: null
depends_on: [AR-107, AR-183, AR-184]
blocks: []
---

# AR-169: Exclude the native PE from portable wheels

> Retired, not completed, on 2026-09-05 under ADR-0219 and AR-197. Both current
> wheel profiles reject PE content; the old requirement to retain the helper in
> the Windows wheel conflicts with the product. AR-160 retains cross-OS artifact
> proof. Historical criteria below remain unchanged, including unproven gates.

## Problem

The Linux producer emits a wheel named and tagged `py3-none-any`, but the actual
wheel still contains the reviewed Windows x86-64 PE. The portable-profile unit
test exercised `build_py.find_data_files` only for the top-level
`agency_runtime` package. Setuptools namespace discovery also treats the native
data directory as a package and invokes the hook with
`agency_runtime.native.windows.operator_presence`, bypassing the top-level-only
filter. The independent verifier correctly rejects both the unexpected payload
and executable content.

## Current state

A detached clean Linux build from the exact reviewed commit passes deterministic
construction and strict package-description checks, then fails independent
portable verification on
`agency_runtime/native/windows/operator_presence/operator_presence_verifier.exe`.
The wheel tag and `Root-Is-Purelib` declaration are therefore not truthful until
the executable is excluded from the built payload.

## Approach

Disable implicit namespace-package discovery because Agency Runtime's Python
packages are regular packages and the native directory is package data. Also
make the portable `build_py` hook derive the exact governed executable path for
every package-prefix depth that setuptools may present. Remove only that exact
path; preserve the C++ source, provenance, licenses/notices, and unrelated
executables. Keep the Windows x64 profile unchanged.

## Dependencies

AR-107 supplies deterministic build and independent verification boundaries.
ADR-0098 requires a portable wheel without the PE and a Windows x64 wheel with
the exact reviewed PE. AR-160 cannot accept the merged release set until both
producer profiles satisfy those contracts. Creating the same-repository tracker
issue remains pending outward-write authorization.

## Acceptance

- [x] Regular package discovery no longer misclassifies native data directories
  as namespace packages.
- [x] The portable filter removes the exact governed PE for both top-level and
  nested package discovery without basename or broad-extension filtering.
- [x] The Windows x64 profile retains the exact reviewed PE.
- [ ] A detached Linux build independently verifies as portable and contains no
  PE; a detached Windows build independently verifies as Windows x64.
- [ ] Both producer source distributions remain byte-identical and the merged
  three-artifact release set independently verifies.
- [ ] Proportionate formatting, tests, documentation validation, and clean-tree
  checks pass.
