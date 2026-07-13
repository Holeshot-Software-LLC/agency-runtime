---
title: "AR-18: Detect work-unit file paths containing spaces"
status: in_progress
category: roadmap
created: 2026-07-13
updated: 2026-07-13
tags: [delegation, portability, testing, windows]
related:
  - docs/decisions/0042-local-only-bounded-work-file-inference.md
  - docs/roadmap/issue-AR-16-linux-python-delegation-compatibility.md
  - docs/roadmap/issue-AR-17-production-hardening-portability.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: testing
issue_id: AR-18
priority: p1
tracker_url: "https://github.com/Holeshot-Software-LLC/agency-runtime/issues/19"
depends_on: []
blocks: [AR-17]
---

# AR-18: Detect work-unit file paths containing spaces

## Problem

Work-unit normalization detected compact path tokens but dropped an existing
absolute file path when the path contained spaces. The missing file set could
weaken shared-file dependency serialization and agent delegation accuracy,
especially for Windows checkouts under paths such as `C:\Workspaces\Project
Name\...`.

## Current state

Explicit `files` fields remained authoritative, but the natural-language path
scanner stopped at the first space. Final Windows validation reproduced the
gap with a real existing Python file beneath the repository's spaced path.
Hosted Linux then showed that the compact scanner could re-read the suffix of
that recovered path as a second root. URL query and fragment values could also
look like local paths and distort worktree conflict inference.

## Approach

Keep the compact parser for planned and nonexistent path tokens. When that
parser finds a path prefix, inspect only bounded supported file suffixes and
accept a longer spaced candidate only when it is an existing regular file.
Pass the recovered file through the existing repository-relative
normalization. Skip matches inside the recovered span and inside the current
URL token, without narrowing assignment or colon-delimited local syntax. Bound
both accepted paths and total scanned candidates. Reject protocol-relative and
network-root tokens before any filesystem probe so automatic inference cannot
trigger outbound share access. This avoids broadly treating surrounding prose
as a path.

## Dependencies

This bug was surfaced by the integrated AR-17 portability gate and complements
AR-16's delegation compatibility work. It blocks AR-17 until the same hosted
Windows and Linux matrix passes and the reviewed fix is merged.

## Acceptance

- [x] Existing absolute file paths containing spaces are captured from
      work-unit descriptions.
- [x] Captured in-repository paths normalize to repository-relative file sets.
- [x] A nonexistent spaced phrase is not reclassified as a file path.
- [x] A recovered path suffix is not emitted as a second local path.
- [x] Path-like URL query and fragment values are not classified as local
      work files.
- [x] Accepted matches and total scanned candidates remain bounded.
- [x] Protocol-relative and network-root tokens are rejected before filesystem
      probing.
- [ ] Warning-strict exact coverage and hosted Windows/Linux matrices pass.
- [ ] The reviewed fix is merged and tracker issue #19 is closed.
