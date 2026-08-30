---
title: "AR-09: Isolate Windows tests from the real user profile"
status: done
category: roadmap
created: 2026-07-10
updated: 2026-07-10
tags: [testing, windows, safety]
related:
  - docs/decisions/0026-explicit-test-home-boundaries.md
supersedes: []
superseded_by: null
type: issue
epic: testing
issue_id: AR-09
priority: p0
tracker_url: "https://github.com/Holeshot-Software-LLC/agency-runtime/issues/9"
depends_on: []
blocks: [AR-07]
---

# AR-09: Isolate Windows tests from the real user profile

## Problem

Tests that claim to isolate host installation can still resolve the real user
profile on Windows. A verification run may overwrite a developer's active host
plugin, while platform-specific path and executable assumptions prevent the
suite from providing a trustworthy release signal.

## Current state

This item is implemented locally. Host-generation APIs now accept an explicit
home boundary, tests and smoke checks pass it directly, and generated artifacts
use UTF-8. Platform-neutral path and executable fixtures replace POSIX and
shell-built-in assumptions. OpenClaw smoke checks validate package structure on
every platform and run a Node syntax check when Node is executable.

The complete suite passes 185 tests on Windows and 185 tests under Ubuntu/WSL.
Hashes and timestamps for the previously affected real-profile Codex plugin
files remained unchanged across the final Windows test run.

## Approach

Make home-directory and temporary-directory resolution injectable at the
installer and test boundaries. In tests, set every platform-relevant profile
variable or pass an explicit destination rather than relying on process-global
home discovery. Replace platform-specific path strings and shell built-ins with
portable fixtures, and add a guard that fails a test before any write escapes
its allocated temporary root.

## Dependencies

None. This blocks release readiness because a release check must not mutate the
machine running it.

## Acceptance

- [x] Host-install tests cannot write outside their allocated temporary root.
- [x] Windows tests do not depend on POSIX path separators.
- [x] Backend availability tests use a real portable fixture executable rather than a shell built-in.
- [x] The full suite passes on Windows and the primary supported non-Windows environment.
- [x] A regression test detects and rejects attempted writes to a real user-profile host directory.
- [x] Test instructions document any required writable temp-root configuration.
