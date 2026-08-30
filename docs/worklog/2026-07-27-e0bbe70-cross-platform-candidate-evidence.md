---
title: "Worklog detail: Cross-platform candidate evidence"
status: active
category: worklog
created: 2026-07-27
updated: 2026-07-27
tags: [production-readiness, release, packaging, ui, dogfood]
related:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-125-workforce-and-one-shot-evaluation.md
  - docs/roadmap/issue-AR-160-publish-platform-honest-native-release-artifacts.md
supersedes: []
superseded_by: null
type: worklog
commit: e0bbe70
short: e0bbe70
date: 2026-07-27
pr: null
related_issues:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-125-workforce-and-one-shot-evaluation.md
  - docs/roadmap/issue-AR-160-publish-platform-honest-native-release-artifacts.md
---

# Worklog detail: Cross-platform candidate evidence

## Purpose

Bind the production verdict to one exact release candidate after clean Windows
and Linux builds, fresh package installs, merged-set verification, and installed
dashboard dogfood.

## Approach

Export exact commit `29da6eca2b0dd73b37a91e6bfdb29881face5d56` into
private clean build roots, produce the host-honest wheel/source pairs, compare
the producer source distributions byte-for-byte, and independently verify the
assembled three-artifact release set. Launch the dashboard from the freshly
installed Windows wheel in an isolated runtime and exercise every navigation
surface plus Refresh and browser-console checks.

## Challenges encountered

The primary checkout contains a user-owned untracked draft and was therefore
inadmissible as a release input. The Linux WSL image lacks Node, so the OpenClaw
generated-plugin syntax subcheck was skipped there; the equivalent packaged
Windows check passed. Generic Codex installation remains deliberately fail
closed because no prepared install transaction or production presence path
exists.

## Decisions and alternatives

One-shot applications remain deferred under ADR-0102. Exhaustive coverage and
compatibility remain owner-requested manual integration work. The evidence is
pinned to the exact tested candidate instead of promoting later documentation
commits to untested package revisions.

## Verification

- Clean Windows wheel/sdist build, strict Twine, independent verification, and
  fresh Python 3.10 wheel/sdist install smoke passed.
- Clean WSL/Linux portable wheel/sdist build, strict Twine, independent
  verification, and fresh Python 3.12 wheel/sdist install smoke passed.
- Producer sdists were byte-identical; the exact three-artifact release verifier
  and strict Twine checks passed.
- Installed Windows-wheel dashboard authentication, seven-section navigation,
  Refresh, truthful Route Lab disablement, and zero browser warnings/errors
  passed. The owned listener was stopped and WSL returned to `Stopped`.
- Documentation validation passed for 448 maintained Markdown files.

## Follow-ups

- [AR-143](../roadmap/issue-AR-143-require-operator-presence-for-controls.md):
  prepare and freeze generic Codex installation before adding a native presence
  operation.
- [AR-161](../roadmap/issue-AR-161-sign-and-license-windows-operator-presence-delivery.md):
  complete signed delivery and the attended canary after owner inputs exist.
- [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md) and
  [AR-125](../roadmap/issue-AR-125-workforce-and-one-shot-evaluation.md): finish
  installed-host and benchmark-valid outcome evidence.
