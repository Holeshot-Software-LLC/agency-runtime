---
title: "Exercise hook-control rejection branches"
status: active
category: worklog
created: 2026-07-20
updated: 2026-07-20
tags: [testing, coverage, runtime-control, security]
related:
  - docs/roadmap/issue-AR-111-honor-global-mode-in-isolated-canaries.md
  - docs/decisions/0076-bind-isolated-canaries-to-explicit-agency-modes.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: worklog
commit: 123910a4d7bb4cd93638d2b28b20af385dd8a28a
short: 123910a
date: 2026-07-20
pr: https://github.com/Holeshot-Software-LLC/agency-runtime/pull/114
related_issues:
  - docs/roadmap/issue-AR-111-honor-global-mode-in-isolated-canaries.md
---

# Worklog detail: Exercise hook-control rejection branches

## Purpose

Restore the repository's exact 100% coverage gate after hosted CI identified two
new defensive branches that behaved correctly but lacked direct assertions.

## Approach

Exercise an absolute path that does not have the canonical
`.agency-runtime/run/control.json` suffix and an authenticated broker response
with an extra top-level field. Both cases must return the fail-enabled master
state and must never reach a trusted authoritative result.

## Challenges encountered

The ordinary invalid-path cases were relative on POSIX, so both stopped at the
absolute-path guard and never reached the suffix guard. Existing malformed
broker tests validated the document body but not the exact response envelope.

## Decisions and alternatives

Coverage exclusions and threshold changes were rejected. The tests assert the
security postcondition rather than merely executing the branches.

## Verification

- Runtime-control suite: 105 passed, 4 platform skips, zero missed statements.
- The two previously missing hosted lines are now executed; the isolated module
  run retains one unrelated Windows-only branch that the complete suite covers.

## Follow-ups

Require the complete hosted combined gate to report 100.00% before merge.
