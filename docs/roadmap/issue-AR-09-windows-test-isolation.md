---
title: "AR-09: Isolate Windows tests from the real user profile"
status: open
category: roadmap
created: 2026-07-10
updated: 2026-07-10
tags: [testing, windows, safety]
related: []
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

The full suite passes 175 tests and fails eight on Windows. Host-install tests
set `HOME`, but the installer resolves the actual Windows profile and one test
run wrote generated Codex plugin files there. Related failures include a POSIX
separator assertion and treating the shell built-in `echo` as a discoverable
executable. Sandbox temp-directory ACL behavior can add noise unless tests use
an explicitly controlled writable root.

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

- [ ] Host-install tests cannot write outside their allocated temporary root.
- [ ] Windows tests do not depend on POSIX path separators.
- [ ] Backend availability tests use a real portable fixture executable rather than a shell built-in.
- [ ] The full suite passes on Windows and the primary supported non-Windows environment.
- [ ] A regression test detects and rejects attempted writes to a real user-profile host directory.
- [ ] Test instructions document any required writable temp-root configuration.
