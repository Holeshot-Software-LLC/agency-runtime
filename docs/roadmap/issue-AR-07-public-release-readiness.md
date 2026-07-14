---
title: "AR-07: Complete public release readiness"
status: in_progress
category: roadmap
created: 2026-07-10
updated: 2026-07-12
tags: [release, packaging]
related:
  - docs/decisions/0010-one-command-install-and-reversible-toggle.md
  - docs/decisions/0025-self-contained-linked-documentation.md
  - docs/decisions/0028-host-support-maturity-and-reversible-install.md
  - docs/decisions/0029-secure-local-dashboard-and-bounded-observability.md
  - docs/decisions/0030-versioned-quantitative-evaluation-gates.md
  - docs/decisions/0034-persistent-soft-host-control.md
  - docs/decisions/0035-authoritative-bounded-provider-chain.md
  - docs/decisions/0036-capability-bound-host-canary-attestations.md
supersedes: []
superseded_by: null
type: issue
epic: release
issue_id: AR-07
priority: p1
tracker_url: "https://github.com/Holeshot-Software-LLC/agency-runtime/issues/7"
depends_on: [AR-03, AR-04, AR-05, AR-06, AR-08, AR-09, AR-10, AR-11, AR-12, AR-13, AR-14, AR-15, AR-16, AR-17]
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
builds wheel/source artifacts, verifies their contents, installs and exercises
both artifacts in isolated Windows/Ubuntu jobs, and runs source/dependency
security checks.

The final local Windows warning-strict coverage run passed `2303` tests with
`5` skips and `2` performance tests deselected. All `17,284` statements and
`5,408` branches had zero missing lines or partial branches (`100.00%`).
Ubuntu 24.04 WSL/Python 3.12 passed `2215` tests with `16` expected
platform/host skips from native ext4, plus both performance tests. The final
performance selection passed both tests (`2308` deselected) with routing p95
`8.640 ms`, cache p95 `0.385 ms`, `155.73` calls/second, and overlap `8`.
All `25` routing gates and `12/12` delegation cases passed. All `60/60`
dashboard JavaScript tests reached exact line, branch, and function coverage
across seven modules, and authenticated Chrome smoke completed without
application console errors.

Codex 0.144.1 is registered and enabled on native Windows. Its authenticated
CLI completed a live keyless judge result, its installed `$agency status` skill
called the status MCP tool, and direct CLI `off`/`on` succeeded. Codex hook
bundle smoke validates the expected events, commands, and timeout schema. The
exact-confirmed isolated-profile canary exited `0`, returned
`canary_passed=true`, produced a valid six-line header with no missing fields,
recorded one routing event and one finalization, and persisted its nonce-bound
attestation. It did not record a model receipt.

The canary used Codex's explicit one-invocation trust bypass inside its private
profile. A separate real-profile `hooks/list` inspection found all three hooks
parser-clean and enabled but untrusted. Durable real-profile trust remains an
operator action through `/hooks`; Agency Runtime reports it as `unverified`
and never queries, mutates, or auto-trusts that store. The isolated result is
not promoted to real-profile `runtime-verified` maturity.

Fresh wheel and source distributions passed build, strict Twine, and structural
verification. Clean Windows/Python 3.14 and WSL/Python 3.12 wheel installs
exercised the MCP server and its ten tools, authenticated dashboard health,
configuration defaults, package assets, and all four generated host bundles.
Final release hygiene, high-severity Bandit, strict offline Zizmor, dependency
consistency and runtime dependency audit, Ruff/format, compile, and whitespace
checks passed.

Those local results and configured workflows are not a completed release:
hosted cross-platform CI, review/merge, the required worklog ledger, and a clean
post-merge tree remain pending. Other absent hosts remain contract-covered
rather than live-verified. Installation from this repository remains the
canonical prerelease path; public package publication is a separate authorized
release action, not an acceptance criterion for release readiness.

## Approach

Create a release checklist that gates claims on verified behavior. Build and install wheel and source artifacts in fresh environments, choose and document the canonical distribution channel, add project governance and security documents, establish version and changelog discipline, and run documentation, packaging, test, secret, and machine-path validation before tagging a release.

## Dependencies

Depends on `AR-03`, `AR-04`, `AR-05`, `AR-06`, `AR-08`, `AR-09`,
`AR-10`, `AR-11`, `AR-12`, `AR-13`, `AR-14`, `AR-15`, `AR-16`, and `AR-17`. A release candidate may explicitly
defer a dependency only by updating its support claims and recording the scope
decision.

## Acceptance

- [x] A fresh environment can install artifacts built from the final reviewed candidate and pass Windows and Linux smoke checks.
- [x] Final-candidate wheel and source distributions contain all required package data and install cleanly.
- [x] Support claims distinguish deterministic contracts from the currently verified host and provider evidence.
- [x] Contribution, security, changelog, troubleshooting, and release-checklist documentation exists.
- [x] Versioning, tagging, and release notes follow a documented repeatable process.
- [x] The post-hook warning-strict suites, exact coverage, documentation validation, secret scanning, and machine-specific path checks pass on the final candidate.
- [ ] Hosted CI passes the supported Python matrix plus security and artifact jobs for the reviewed commit.
- [x] The isolated Codex header canary passes with truthful profile scope; durable
      real-profile `/hooks` trust remains an explicit operator installation
      step and is not claimed by the canary.
- [ ] The reviewed changes are merged with the required worklog ledger and a
      clean resulting tree.
