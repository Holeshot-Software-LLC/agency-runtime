---
title: "AR-107: Build release artifacts from canonical Git blobs"
status: in_progress
category: roadmap
created: 2026-07-19
updated: 2026-07-20
tags: [release, packaging, windows, portability, reproducibility]
related:
  - .github/workflows/ci.yml
  - scripts/build_distributions.py
  - scripts/canonicalize_distributions.py
  - scripts/release_contract.py
  - scripts/release_git.py
  - scripts/verify_distribution.py
  - docs/RELEASE_CHECKLIST.md
  - CONTRIBUTING.md
  - docs/roadmap/issue-AR-108-atomic-owned-process-containment.md
  - docs/decisions/0037-layered-pinned-supply-chain-gates.md
  - docs/decisions/0073-own-subprocess-trees-atomically.md
  - docs/decisions/0074-build-byte-deterministic-release-artifacts.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: release
issue_id: AR-107
priority: p0
tracker_url: "https://github.com/Holeshot-Software-LLC/agency-runtime/issues/109"
depends_on:
  - AR-108
blocks: []
---

# AR-107: Build release artifacts from canonical Git blobs

## Problem

A clean Windows checkout with `core.autocrlf=true` can retain filtered CRLF
working-tree bytes for files whose committed Git blobs use LF. Building directly
from that working tree embeds bytes that do not match the reviewed commit. The
exact distribution verifier correctly rejects the wheel and source distribution,
but the documented PowerShell release path does not provide a portable way to
materialize canonical source bytes before building.

## Current state

The hosted artifact job builds on Ubuntu, where the checkout matches canonical
Git bytes, and its Windows artifact smoke therefore passes. A local Windows
release operator can follow the documented clean-checkout commands and still
produce noncanonical artifacts because Git's clean status compares filtered
content rather than the physical bytes consumed by the build backend. Weakening
the verifier or normalizing source payloads after construction would hide the
provenance failure. Container metadata created by the pinned backend also varies
by operating system, so it needs one explicit normalization policy that never
changes a source or generated payload.

## Approach

Add one cross-platform release builder that requires a full reviewed commit,
binds it to a clean live `HEAD`, materializes the exact committed tree in a
private temporary directory, and validates every extracted regular file and
mode against `git ls-tree` blob identities. Reject unsafe names, aliases, links,
special entries, missing files, transformed content, and output collisions
before invoking the build backend. Validate the bounded backend output against a
finite Windows/Linux source-header allowlist, then repack it with an explicit
stored-ZIP writer, an owned canonical RFC 1951 stored-block gzip encoder, and one
PAX-tar container policy while preserving every payload byte.
Revalidate live `HEAD`, checkout cleanliness, artifact identities, and bounded
content before atomically publishing exactly one wheel and one source
distribution. Use that helper in CI and in every documented release command
while keeping the distribution verifier independently implemented, invoked, and
semantically strict. Require the hosted Windows and Linux builds to exchange
their complete pairs and prove filename and byte equality before either pair can
feed an installation or publication workflow.

## Dependencies

AR-108 supplies the atomic owned-process boundary used for every release Git
and build-backend subprocess. This issue closes a release-operator portability
gap discovered while building the exact merge commit from PR #104 on Windows.

## Acceptance

- [x] The builder requires one full canonical reviewed commit and a clean matching live `HEAD` before and after construction.
- [x] Release source bytes and file modes come from the reviewed Git tree, independent of checkout line-ending filters.
- [x] Unsafe, aliasing, linked, special, missing, transformed, or over-budget archive entries fail before the build backend runs.
- [x] Bounded backend outputs normalize to one byte-deterministic cross-platform container policy without changing payload bytes or depending on host-zlib output.
- [ ] Hosted Windows and Linux builds produce byte-identical wheel/source pairs before the reviewed Linux pair can become an install or publication candidate.
- [x] The destination cannot overwrite prior artifacts, and failed builds do not publish a partial destination.
- [x] A successful build publishes exactly one wheel and one source distribution for independent strict verification.
- [ ] A regression with `core.autocrlf=true` proves canonical LF blobs survive materialization on every platform.
- [x] CI, contributor guidance, and the release checklist use the canonical builder.
- [x] Focused tests, warning-strict coverage, Ruff, documentation, and distribution verification pass.
