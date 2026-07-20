---
title: "AR-109: Make hosted process-security tests race-free and platform-honest"
status: in_progress
category: roadmap
created: 2026-07-20
updated: 2026-07-20
tags: [testing, portability, processes, security, ci]
related:
  - docs/roadmap/issue-AR-104-run-hosted-portability-gates-in-trusted-boundaries.md
  - docs/roadmap/issue-AR-108-atomic-owned-process-containment.md
  - docs/decisions/0073-own-subprocess-trees-atomically.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: testing
issue_id: AR-109
priority: p0
tracker_url: "https://github.com/Holeshot-Software-LLC/agency-runtime/issues/112"
depends_on: [AR-104, AR-108]
blocks: [AR-107]
---

# AR-109: Make hosted process-security tests race-free and platform-honest

## Problem

Hosted Linux exposed two test-contract defects. A Windows executable-suffix
simulation supplied a POSIX absolute path to an explicit NT lexical-path
boundary, so it failed before reaching the intended suffix guard. Process-
containment tests also treated PID-file existence as proof that the PID payload
was complete; Python 3.14 observed an empty file between creation and write
completion.

## Current state

PR #111's hosted Python 3.13 and 3.14 Linux cells captured the failures. Product
path and containment logic remained fail-closed. The corrected simulations pass
on Windows and native WSL; the complete hosted rerun remains required.

## Approach

Model the Windows suffix boundary with one absolute NT spelling and a frozen
regular-file identity instead of asking a POSIX path to masquerade as NT. Add a
shared test readiness predicate that parses every PID file as a positive integer
before any immediate read, and use it across affected Linux and Windows process
lifecycle tests.

## Dependencies

AR-104 owns trusted hosted portability boundaries. AR-108 owns atomic process
containment and descendant cleanup.

## Acceptance

- [x] The NT suffix simulation reaches the intended suffix guard on POSIX without weakening production path validation.
- [x] PID readiness requires a complete positive integer rather than file existence.
- [x] Affected Windows and native Linux tests pass warning-strict.
- [ ] The complete hosted Python matrix passes on PR #111.
- [x] Documentation, worklog, and tracker mapping remain synchronized.
