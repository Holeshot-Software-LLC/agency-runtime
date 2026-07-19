---
title: "AR-104: Run hosted portability gates in trusted boundaries"
status: in_progress
category: roadmap
created: 2026-07-19
updated: 2026-07-19
tags: [testing, portability, security, linux, windows, ci, python]
related:
  - docs/roadmap/issue-AR-17-production-hardening-portability.md
  - docs/roadmap/issue-AR-103-import-windows-ctypes-fixtures-portably.md
  - docs/decisions/0030-versioned-quantitative-evaluation-gates.md
  - docs/decisions/0040-preserve-environment-owned-python-launchers.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: testing
issue_id: AR-104
priority: p0
tracker_url: "https://github.com/Holeshot-Software-LLC/agency-runtime/issues/106"
depends_on:
  - AR-103
blocks: []
---

# AR-104: Run hosted portability gates in trusted boundaries

## Problem

The hardened runtime correctly rejects launchers, configuration, databases, and
temporary paths that another operating-system account can replace. GitHub's
Linux runner exposes its tool cache and runner-temp hierarchy with permissions
that intentionally do not satisfy that production trust contract. The test
matrix was also injecting shared configuration/database overrides into every
test, while several Windows API fixtures assumed Windows-only `ctypes` members
and drive-qualified temporary paths. As a result, hosted CI produced hundreds
of downstream failures even though the production controls were behaving
correctly. The built wheel also used one Python 3.11-only datetime alias despite
declaring Python 3.10 support, and roster-audit hashes depended on checkout line
endings.

## Current state

PR #104 exposed the defects after the first POSIX collection repair. The
failures have been classified into Python-floor compatibility, hosted-runner
trust boundaries, process-wide test-environment contamination, host-specific
Windows fixtures, and noncanonical audit text hashes. Production path and
launcher validation remains intentionally unchanged while the harness is
repaired.

## Approach

Run Linux tests through an exact private copy of the selected Python
interpreter, place pytest/home state beneath a current-user-owned private
namespace, and remove suite-wide configuration/database overrides. Keep
per-test runtime state isolated in the shared fixture. Model Windows path and
API behavior through explicit injected seams instead of relying on the host
`ctypes` surface or mutating the shared `os` module. Replace Python 3.11-only
datetime usage with the supported timezone API. Hash tracked UTF-8 audit text
using canonical LF bytes so Windows and Linux verify the same immutable
content.

## Dependencies

AR-103 owns the initial `ctypes.wintypes` collection defect. ADR-0030 requires
the matrix to be deterministic, and ADR-0040 requires environment-owned
launchers to remain intact in production; the private launcher copy is a
test-only execution boundary.

## Acceptance

- [ ] The package imports and artifact smoke passes on Python 3.10.
- [ ] Linux tests run from a current-user-owned, non-writable launcher namespace.
- [ ] Tests receive isolated home/runtime state without global config or database overrides.
- [ ] Windows API and path simulations pass on both Windows and POSIX.
- [ ] Roster-audit integrity is invariant across LF and CRLF working trees.
- [ ] Warning-strict tests, exact coverage, performance, dashboard, artifact, Windows, and Linux hosted gates pass.
