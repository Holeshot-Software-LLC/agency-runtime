---
title: "AR-07: Complete public release readiness"
status: open
category: roadmap
created: 2026-07-10
updated: 2026-07-10
tags: [release, packaging]
related:
  - docs/decisions/0010-one-command-install-and-reversible-toggle.md
  - docs/decisions/0025-self-contained-linked-documentation.md
supersedes: []
superseded_by: null
type: issue
epic: release
issue_id: AR-07
priority: p1
tracker_url: "https://github.com/Holeshot-Software-LLC/agency-runtime/issues/7"
depends_on: [AR-03, AR-04, AR-05, AR-06, AR-08, AR-09]
blocks: []
---

# AR-07: Complete public release readiness

## Problem

A public release needs reproducible installation, truthful capability claims, contributor and security guidance, tested artifacts, and a versioned release process. A detailed README alone is not a release gate.

## Current state

The project has package metadata, an MIT license, a broad automated test suite, a canonical Git-based installation path, self-contained documentation, and substantial README guidance. Host support claims still exceed the evidence described in `AR-03`, and the repository lacks dedicated contributor, security, changelog, release-checklist, and troubleshooting documents. No published-package claim is established by repository evidence.

## Approach

Create a release checklist that gates claims on verified behavior. Build and install wheel and source artifacts in fresh environments, choose and document the canonical distribution channel, add project governance and security documents, establish version and changelog discipline, and run documentation, packaging, test, secret, and machine-path validation before tagging a release.

## Dependencies

Depends on `AR-03`, `AR-04`, `AR-05`, `AR-06`, `AR-08`, and `AR-09`. A release candidate may explicitly defer a dependency only by updating its support claims and recording the scope decision.

## Acceptance

- [ ] A fresh environment can install from the documented canonical source and pass smoke checks.
- [ ] Wheel and source distributions contain all required package data and install cleanly.
- [ ] Support claims match the verified host and provider matrix.
- [ ] Contribution, security, changelog, troubleshooting, and release-checklist documentation exists.
- [ ] Versioning, tagging, and release notes follow a documented repeatable process.
- [ ] Tests, documentation validation, secret scanning, and machine-specific path checks pass before release.
