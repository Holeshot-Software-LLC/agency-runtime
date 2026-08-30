---
title: "AR-72: Align release tooling and artifact verification"
status: done
category: roadmap
created: 2026-07-16
updated: 2026-07-16
tags: [release, packaging, ci, cli, supply-chain, verification]
related:
  - docs/decisions/0037-layered-pinned-supply-chain-gates.md
  - docs/RELEASE_CHECKLIST.md
  - CONTRIBUTING.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: release
issue_id: AR-72
priority: p0
tracker_url: "https://github.com/Holeshot-Software-LLC/agency-runtime/issues/73"
depends_on: []
blocks: []
---

# AR-72: Align release tooling and artifact verification

## Problem

Release-readiness audit found drift between the project build dependency and
CI, which still installed a yanked build version. CI did not bind installed
smoke evidence to the expected package version, the CLI lacked the documented
top-level version surface, and distribution verification enforced only a
partial source-payload contract. Those gaps could allow misleading or
incomplete release evidence to pass.

## Current state

The package already uses pinned build tooling, reproducible wheel and sdist
checks, isolated installed-distribution smoke scripts, artifact metadata
verification, dependency auditing, and a release checklist. The remaining
defect is inconsistent enforcement across those surfaces rather than missing
release architecture.

## Approach

Use one non-yanked build pin in project and workflows, require CI installed
smoke to assert the canonical package version, expose that version through
`agency --version`, and make distribution verification enforce the complete
intended release script/test payload while rejecting unexpected package source
files. Add parity regressions so future workflow or artifact drift fails early.

## Dependencies

ADR-0037 governs the layered pinned supply-chain gate. This issue tightens that
existing contract without publishing an artifact, creating a tag, or changing
the public release authorization boundary.

## Acceptance

- [x] Project and workflow build pins use the same current non-yanked version.
- [x] CI installed smoke requires the canonical expected package version.
- [x] `agency --version` reports the canonical installed package version.
- [x] Distribution verification requires the complete intended release payload.
- [x] Unexpected package source files in wheel or sdist fail verification.
- [x] Focused parity, CLI, packaging, and artifact-verifier regressions pass.
- [x] Clean wheel and sdist build, metadata, isolation, and installed-smoke gates pass on Windows and Linux.
- [x] Full-suite, tracker, and merged-install gates pass.
