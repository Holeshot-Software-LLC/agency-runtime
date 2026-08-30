---
title: "Worklog detail: Reuse one attested launcher for all-host smoke"
status: active
category: worklog
created: 2026-07-27
updated: 2026-07-27
tags: [smoke, performance, packaging, launcher, security]
related:
  - docs/worklog/README.md
  - docs/roadmap/README.md
  - docs/roadmap/issue-AR-160-publish-platform-honest-native-release-artifacts.md
  - docs/roadmap/issue-AR-181-bound-all-host-smoke-launcher-preparation.md
supersedes: []
superseded_by: null
type: worklog
commit: c625bc76707e169f4c4100fb6dc1247bbddb77c7
short: c625bc7
date: 2026-07-27
pr: null
related_issues:
  - docs/roadmap/issue-AR-160-publish-platform-honest-native-release-artifacts.md
  - docs/roadmap/issue-AR-181-bound-all-host-smoke-launcher-preparation.md
---

# Worklog detail: Reuse one attested launcher for all-host smoke

## Purpose

Remove repeated hashing of the same 821-file private runtime from the bounded
all-host smoke command while preserving the launcher's attestation and host
identity guarantees.

## Approach

Multi-host smoke now lazily prepares one attested launcher artifact and binds
its exact paths around each isolated host check. A preparation failure is cached
only for that invocation and remains a typed failure for every affected host;
single-host smoke retains the existing path.

## Challenges encountered

A fresh installed-runtime command exceeded the 122.4-second observation ceiling.
A bounded faulthandler snapshot localized the delay to five sequential calls
that each rehashed the same private package runtime. The installed-distribution
smoke itself completed in 3.5 seconds, separating packaging correctness from the
avoidable all-host orchestration cost.

## Decisions and alternatives

The implementation preserves private runtime preparation, exact artifact
identity, and per-host launcher verification. Globally caching mutable source
state or bypassing preparation was rejected because either approach would weaken
the existing trust boundary.

## Verification

- The focused smoke suites passed all 34 cases.
- Release-packaging and CLI-parser suites passed all 142 cases.
- A real source `agency smoke --all --json` passed 8 checks with no failures or
  skips in 43.9 seconds, compared with the pre-fix run exceeding 122.4 seconds.
- Ruff check, Ruff format, documentation validation, and `git diff --check`
  passed.
- No exhaustive Python corpus, compatibility matrix, hosted workflow, or push
  ran.

## Follow-ups

- Rebuild and re-run the smoke check from the exact final fresh wheel under
  [AR-160](../roadmap/issue-AR-160-publish-platform-honest-native-release-artifacts.md).
- Create and synchronize the AR-181 tracker item only after explicit outward
  authorization.
