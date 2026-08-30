---
title: "Worklog: Bound child routing review fixes and parallelize CI"
status: active
category: worklog
created: 2026-07-21
updated: 2026-07-21
tags: [routing, delegation, ci, coverage, dashboard]
related:
  - docs/roadmap/issue-AR-115-live-routing-trust.md
  - docs/roadmap/issue-AR-116-bound-child-routing-and-oauth-model-selection.md
  - docs/roadmap/issue-AR-117-parallelize-pr-verification.md
supersedes: []
superseded_by: null
type: worklog
commit: 49e8f996b8fdf8af03c1ee99a39c0d9a3e3a19b6
short: 49e8f99
date: 2026-07-21
pr: https://github.com/Holeshot-Software-LLC/agency-runtime/pull/129
related_issues:
  - docs/roadmap/issue-AR-115-live-routing-trust.md
  - docs/roadmap/issue-AR-116-bound-child-routing-and-oauth-model-selection.md
  - docs/roadmap/issue-AR-117-parallelize-pr-verification.md
---

# Worklog: Bound child routing review fixes and parallelize CI

## Purpose

Close five review defects that could bypass native-child inference bounds, make
the dashboard tolerate malformed account-model catalogs, and shorten hosted
feedback without weakening the repository's exact coverage requirement.

## Approach

OpenClaw now projects parent correlation through its bounded bridge. Child
singleflight leases and coalescing waits derive from the longest configured
judge/provider timeout with a bounded safety margin. Budget abstention stops
exact-unit inference, and heuristic fallback evaluates the filtered candidate
score. Regression tests exercise each boundary.

The CI workflow retains its established required-check name for branch
protection, but moves Python coverage into four deterministic size-balanced
jobs, combines their data, and enforces the same 100% line-and-branch threshold.
Performance runs independently. A deterministic selector and workflow-contract
tests guarantee complete, disjoint test-file assignment.

## Challenges encountered

A local full-coverage attempt used `C:\tmp`, whose cross-account-writable ACL was
correctly rejected by the runtime security tests; that result was discarded.
The faster dashboard gate then exposed an unhandled `null` account-model row and
newly added provider branches below 100% coverage. The catalog projection and
tests were hardened until the UI returned to exact coverage.

## Decisions and alternatives

Sharding uses a dependency-free greedy file-size balance instead of adding a
pytest sharding plugin. Coverage remains an aggregate repository invariant, not
a relaxed per-shard threshold. The compatibility, portability, security, and
artifact matrices remain intact.

## Verification

- Focused routing, adapter, CLI, workflow, and release contracts: 161 passed.
- Dashboard UI: 93 passed; 100% lines, branches, and functions.
- Ruff lint and formatting: passed across package, tests, and scripts.
- Documentation validation: passed for 267 Markdown files with tracker parity.
- Git whitespace validation: passed.

## Follow-ups

Hosted CI must prove shard execution and recombination before PR #129 merges.
After merge, install the merged artifact into this Codex and run live routing,
model discovery, header, configuration, and dashboard smoke tests.
