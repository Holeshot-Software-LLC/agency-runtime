---
title: "Worklog detail: Normalize owner-private POSIX wheel modes"
status: active
category: worklog
created: 2026-07-27
updated: 2026-07-27
tags: [release, packaging, linux, reproducibility, security]
related:
  - docs/worklog/README.md
  - docs/roadmap/README.md
  - docs/roadmap/issue-AR-183-normalize-private-posix-wheel-modes.md
  - docs/decisions/0074-build-byte-deterministic-release-artifacts.md
supersedes: []
superseded_by: null
type: worklog
commit: d07f4d8
short: d07f4d8
date: 2026-07-27
pr: null
related_issues:
  - docs/roadmap/issue-AR-183-normalize-private-posix-wheel-modes.md
---

# Worklog detail: Normalize owner-private POSIX wheel modes

## Purpose

A detached Linux release build under the required restrictive `umask 077`
failed before canonicalization because wheel 0.47.0 encoded non-executable
ordinary members as owner-private `0600`. The canonicalizer previously accepted
only POSIX `0644`, so a safer source permission blocked the portable producer.

## Approach

Keep the source-wheel contract finite and platform-specific. POSIX ordinary
regular files may enter with exact `0600` or `0644`; Windows ordinary members
and RECORD retain their exact existing modes. Both raw central-record and
`ZipInfo` validation share the same allowlist, and canonical output still emits
ordinary `0644` and RECORD `0664`.

## Challenges encountered

Raw inspection of the failed restrictive build found 559 ordinary `0600`
members, one ordinary `0644` member, and RECORD at `0664`. A control build from
a checkout whose files were `0644` still emitted a mixed 267/293 split under
`umask 077`, proving the behavior came from the pinned build backend rather than
unsafe repository modes.

## Decisions and alternatives

The build keeps `umask 077`; weakening the producer boundary was rejected.
Post-build blanket `chmod` and broad permission-mask acceptance were also
rejected because they would obscure source metadata or admit executable and
special-file modes. The exact additional input is POSIX regular `0600` only.

## Verification

- The four-file canonicalizer, verifier, build, and release package passed 383
  tests in 139.36 seconds.
- The expanded canonicalizer boundary suite passed 83 tests in 1.07 seconds.
- Independent security, release, and regression reviews found no production
  defect; all identified defense-in-depth test gaps were added.
- Ruff check, Ruff format check, documentation verification, and
  `git diff --check` passed.

## Follow-ups

Run a committed detached Linux producer under `umask 077`, prove strict Twine
and portable verification, compare its sdist byte-for-byte with Windows, and
verify the merged three-file release set under
[AR-183](../roadmap/issue-AR-183-normalize-private-posix-wheel-modes.md).
