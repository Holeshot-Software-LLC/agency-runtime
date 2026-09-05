---
title: "AR-405 portable directory-identity regression repair"
status: active
category: worklog
created: 2026-09-05
updated: 2026-09-05
tags: [testing, release, portability, backlog]
related:
  - docs/roadmap/issue-AR-405-make-directory-identity-regressions-portable.md
  - docs/roadmap/acceptance/evidence/AR-405-portable-directory-identity-20260905.md
  - docs/decisions/0074-build-byte-deterministic-release-artifacts.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: worklog
commit: 593f074fc2e9e302efc9a20cdc2c82ce98637bb0
short: 593f074f
date: 2026-09-05
pr: https://github.com/Holeshot-Software-LLC/agency-runtime/pull/678
related_issues:
  - docs/roadmap/issue-AR-405-make-directory-identity-regressions-portable.md
  - docs/roadmap/issue-AR-404-evidence-led-backlog-completion.md
---

# Worklog: portable directory-identity regression repair

## Purpose and approach

The preceding backlog review found two tests importing a historical Windows
filesystem assumption into Linux. Reproduce them before changing anything,
retain portable real filesystem I/O and replacement tests, and model the
volatile attribute explicitly in local synthetic metadata. Preserve the native
Windows observation separately with a platform/filesystem premise guard.

## Challenges and alternatives

The original code repair in 71833c5c remains correct for this reproduction;
changing production identity semantics or skipping the whole family would hide
the actual fixture problem. No native Windows execution is available. History
is retained as history, not relabeled as a current platform pass. The first
documentation draft needed its empty Verification table and line-bound source
citations corrected before its gate passed; no verdict was fabricated.

## Verification

Before: build-test file 91 passed, two failed (8.04s). After: 100 passed, one
native-only skip (5.25s); wider seven files 452 passed, three skipped (11.68s).
Named fast spine: 1004 passed, three skipped (63.23s). UI 138 passed. Ruff,
format, metadata, policy, worklog and strict docs checks pass; deterministic
routing gates pass. Isolated acceptance is
now satisfied for all three criteria at 970293d7. The first conformance run
failed its copied baseline's private-directory setup under ambient umask 0002;
source was unchanged and no mutations ran. The protected umask 077 rerun follows
the existing AR-297 procedure and passed baseline (99.433s) plus 182/182
mutation kills, with zero invalid/survived and source unchanged. No existing
permissions or trust policy changed.
No host mutation, native Windows run or exhaustive workflow occurred.

## Follow-ups

Candidate 593f074f has three satisfied isolated verdicts. PR #678 carries the
verified closure recorded by 24e37e33. AR-271 is the next genuine runtime fix.
The existing runtime payload is unchanged by this test-only package.
