---
title: "AR-07: Complete public release readiness"
status: in_progress
category: roadmap
created: 2026-07-10
updated: 2026-07-11
tags: [release, packaging]
related:
  - docs/decisions/0010-one-command-install-and-reversible-toggle.md
  - docs/decisions/0025-self-contained-linked-documentation.md
  - docs/decisions/0028-host-support-maturity-and-reversible-install.md
  - docs/decisions/0029-secure-local-dashboard-and-bounded-observability.md
  - docs/decisions/0030-versioned-quantitative-evaluation-gates.md
supersedes: []
superseded_by: null
type: issue
epic: release
issue_id: AR-07
priority: p1
tracker_url: "https://github.com/Holeshot-Software-LLC/agency-runtime/issues/7"
depends_on: [AR-03, AR-04, AR-05, AR-06, AR-08, AR-09, AR-10, AR-11, AR-12, AR-13, AR-14]
blocks: []
---

# AR-07: Complete public release readiness

## Problem

A public release needs reproducible installation, truthful capability claims, contributor and security guidance, tested artifacts, and a versioned release process. A detailed README alone is not a release gate.

## Current state

The project now has package metadata, an MIT license, truthful contract-versus-
live support documentation, contribution and security policies, a changelog,
troubleshooting guidance, and a release checklist. CI is configured for Python
3.10 through 3.14 on Ubuntu and the 3.10/3.14 support endpoints on Windows,
builds wheel/source artifacts, verifies their contents, installs the wheel in
isolated Windows/Ubuntu jobs, and runs source/dependency security checks.

Local release validation passed 433 tests with one expected POSIX-only skip,
Windows and isolated Ubuntu/WSL routing, delegation, generated-host smoke, and
packaged-dashboard checks, strict wheel/source metadata and content checks,
clean wheel and source-distribution installs, dependency validation, real
browser verification, and source/dependency security scans.

Those local results and the configured workflows are not a completed release:
this branch does not contain a confirmed clean hosted cross-platform CI run,
live host canaries for the claimed v1 matrix, or evidence of a published public
package. Installation from this repository remains the canonical prerelease
path.

## Approach

Create a release checklist that gates claims on verified behavior. Build and install wheel and source artifacts in fresh environments, choose and document the canonical distribution channel, add project governance and security documents, establish version and changelog discipline, and run documentation, packaging, test, secret, and machine-path validation before tagging a release.

## Dependencies

Depends on `AR-03`, `AR-04`, `AR-05`, `AR-06`, `AR-08`, `AR-09`,
`AR-10`, `AR-11`, `AR-12`, and `AR-13`. A release candidate may explicitly
defer a dependency only by updating its support claims and recording the scope
decision.

## Acceptance

- [x] A fresh environment can install from the documented canonical source and pass smoke checks.
- [x] Wheel and source distributions contain all required package data and install cleanly.
- [x] Support claims distinguish deterministic contracts from the currently verified host and provider evidence.
- [x] Contribution, security, changelog, troubleshooting, and release-checklist documentation exists.
- [x] Versioning, tagging, and release notes follow a documented repeatable process.
- [x] Tests, documentation validation, secret scanning, and machine-specific path checks pass before release.
