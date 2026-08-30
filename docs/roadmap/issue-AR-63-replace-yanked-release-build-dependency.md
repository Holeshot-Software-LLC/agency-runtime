---
title: "AR-63: Replace the yanked release-build dependency"
status: done
category: roadmap
created: 2026-07-16
updated: 2026-07-16
tags: [release, supply-chain, dependencies, packaging, testing]
related:
  - docs/decisions/0037-layered-pinned-supply-chain-gates.md
  - docs/RELEASE_CHECKLIST.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: release
issue_id: AR-63
priority: p0
tracker_url: "https://github.com/Holeshot-Software-LLC/agency-runtime/issues/64"
depends_on: []
blocks: []
---

# AR-63: Replace the yanked release-build dependency

## Problem

The pinned `build==1.5.1` release-tool dependency was yanked by its publisher
because it contains changes being reconsidered for a new major release. A
fresh Ubuntu installation emits the yanked-release warning, so retaining the
pin would make the release environment knowingly non-reproducible against the
publisher's supported stable line.

## Current state

The release extra pins `build==1.5.0`, the current non-yanked stable release on
PyPI. Runtime dependencies are unchanged; this affects only maintainers and CI
jobs that build source and wheel artifacts.

## Approach

Keep release tools exactly pinned, but follow the publisher's stable release
line rather than a yanked artifact. Recreate clean Windows and Ubuntu release
environments, build both distributions, run strict metadata and content
verification, and smoke-install each artifact.

## Dependencies

ADR-0037 requires pinned, layered supply-chain gates. This correction preserves
that decision while replacing an upstream-withdrawn input.

## Acceptance

- [x] The release extra contains no yanked `build` version.
- [x] Fresh Windows and Ubuntu release environments install without a yanked-version warning.
- [x] Source and wheel builds pass strict metadata and distribution verification.
- [x] Both artifacts smoke-install and pass `pip check` on Windows and Ubuntu.
- [x] Vulnerability, workflow, and release-hygiene gates remain clean.
