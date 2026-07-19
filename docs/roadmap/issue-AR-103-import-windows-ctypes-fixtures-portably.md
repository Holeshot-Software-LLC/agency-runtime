---
title: "AR-103: Import Windows ctypes fixtures portably on POSIX"
status: in_progress
category: roadmap
created: 2026-07-19
updated: 2026-07-19
tags: [testing, portability, windows, linux, ci]
related:
  - docs/roadmap/issue-AR-17-production-hardening-portability.md
  - docs/decisions/0030-versioned-quantitative-evaluation-gates.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: testing
issue_id: AR-103
priority: p0
tracker_url: "https://github.com/Holeshot-Software-LLC/agency-runtime/issues/105"
depends_on: []
blocks: []
---

# AR-103: Import Windows ctypes fixtures portably on POSIX

## Problem

Two Windows ACL test fixtures access `ctypes.wintypes.DWORD` during module
collection without importing the `ctypes.wintypes` submodule. Windows imports
happen to populate that attribute indirectly, but POSIX Python does not
guarantee it. The Ubuntu Python 3.11 and 3.14 jobs therefore fail before running
any tests.

## Current state

PR #104 produced the same collection error in both hosted jobs. The fixtures
now import `wintypes` explicitly and bind their test-only structure fields to
that module. Production ACL behavior is unchanged; hosted matrix proof remains.

## Approach

Import `wintypes` from `ctypes` in both cross-platform fixture modules. Keep the
test structures and simulated Windows API behavior otherwise identical, then
require focused Windows execution plus the complete hosted Windows/Linux
matrix.

## Dependencies

The defect was discovered by the release support matrix. It has no production
runtime dependency.

## Acceptance

- [x] Both fixture modules import the Windows type definitions explicitly.
- [x] Windows ACL fixture behavior remains unchanged locally.
- [x] Ruff and focused warning-strict tests pass.
- [ ] PR #104 hosted Windows/Linux matrix passes.
