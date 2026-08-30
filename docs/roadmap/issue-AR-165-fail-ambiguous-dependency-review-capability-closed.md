---
title: "AR-165: Fail ambiguous dependency-review capability probes closed"
status: in_progress
category: roadmap
created: 2026-07-27
updated: 2026-07-27
tags: [security, supply-chain, ci, performance, cost, github-actions]
related:
  - docs/roadmap/issue-AR-156-restore-cost-bounded-verification.md
  - docs/roadmap/issue-AR-159-enforce-production-branch-protection.md
  - docs/roadmap/issue-AR-162-collapse-unavailable-codeql-fanout.md
  - docs/decisions/0037-layered-pinned-supply-chain-gates.md
  - docs/decisions/0097-gate-expensive-ci-fanout-behind-quality-contracts.md
  - .github/workflows/dependency-review.yml
  - tests/test_release_packaging.py
supersedes: []
superseded_by: null
type: issue
epic: security
issue_id: AR-165
priority: p0
tracker_url: null
depends_on: []
blocks: [AR-159]
---

# AR-165: Fail ambiguous dependency-review capability probes closed

## Problem

The pull-request dependency-review workflow treated every HTTP 403 or 404 from
GitHub's dependency-diff endpoint as proof that native dependency review was
unavailable. Authentication failures, missing resources, rate limiting, and
other ambiguous API responses could therefore select the installed-runtime
`pip-audit` fallback and let the stable `dependency review` check pass without
reviewing the pull request's base-to-head dependency changes.

The fallback is useful compensating vulnerability evidence, but it is not
equivalent to dependency-diff review: it cannot decide which dependencies the
pull request introduced or changed. Conflating those controls weakens the
release gate and makes a green check overstate the evidence it produced.

## Current state

An authenticated read-only live probe against the current private, non-fork
repository returned HTTP 403 with exactly GitHub's documented dependency-review
capability-unavailable JSON tuple: `message` `Forbidden`, the dependency-review
comparison documentation URL, and string `status` `403`. The repository identity
endpoint independently returned HTTP 200 and proved the expected repository,
visibility, fork state, and token pull authority. No response headers or token
values were retained.

A historical successful dependency-review job consumed 0.43 raw runner-minutes.
Current hosted validation is unavailable because GitHub rejects new jobs at the
external Actions billing or spending-limit boundary before workflow steps run.
Neither number proves the replacement faster or predicts rounded billing.

## Approach

Keep one stable `dependency review` job. Capture the authenticated repository
identity and dependency comparison bodies into runner-owned temporary files with
strict connection, total-time, and response-size bounds. Treat command or network
failure as failure before classification.

Accept native review after a well-formed HTTP 200 comparison. Accept the
unavailable path only after the repository identity response proves the exact
private or internal non-fork repository and read authority, and the comparison
response is the exact observed/documented HTTP 403 JSON tuple. Reject HTTP 401,
404, rate-limit responses, malformed status or JSON, unexpected fields, public
or fork scope, repository mismatch, missing pull authority, oversized files, and
all other ambiguity.

Run the pinned installed-runtime vulnerability audit only on that positively
identified boundary and label it explicitly as non-equivalent compensating
evidence. End the same job with an `always()` aggregate that accepts only a
fully successful native path or a fully successful recognized fallback path.
This adds no hosted job and prevents a probe from waiting until the job ceiling.

## Dependencies

ADR-0037 governs layered pinned supply-chain gates and the distinction between
native dependency-diff review and runtime vulnerability auditing. ADR-0097
governs cost-conscious fail-closed CI topology and stable aggregate checks.
AR-159 may require this stable check only after current hosted behavior and
repository protection are authorized and verified.

## Acceptance

- The workflow retains one least-privilege job named `dependency review`.
- Repository and comparison requests use authenticated runner-owned files with
  bounded connect time, total time, response size, and explicit curl-failure
  handling; no header or token value is emitted as output evidence.
- HTTP 200 comparison JSON selects the unchanged pinned native dependency-review
  action and moderate-severity failure threshold.
- Only the exact authenticated private/internal non-fork HTTP 403 response tuple
  selects fallback; 401, 404, rate-limit, malformed, oversized, public, fork,
  identity-mismatch, and authority-mismatch cases fail closed.
- The fallback installs the project with its runtime dependencies, uses the
  pinned audit tool, and is labeled as compensating evidence rather than
  equivalent base-to-head dependency review.
- One `always()` aggregate rejects failed, cancelled, skipped, missing, invalid,
  or cross-path-incoherent prerequisite results.
- Executable contract tests cover both coherent paths and adversarial API,
  repository-identity, bounded-file, and aggregate-result cases.
- One matched hosted pull-request run records the selected path, stable check
  name, and raw duration before any speed or billing-savings claim is accepted.
- The tracker issue and local roadmap record have exact URL/state parity after
  tracker creation is authorized.

## Implementation evidence

The local workflow now performs two bounded authenticated probes, validates
runner-owned JSON files and repository identity before classification, rejects
every response except a valid HTTP 200 comparison or the exact scoped HTTP 403
capability tuple, preserves the pinned native action, labels the pinned runtime
audit honestly, and converges on one stable fail-closed aggregate without adding
a runner.

Focused tests execute both accepted classifications and both accepted aggregate
states. They reject ambiguous 403 bodies, rate-limit, 401, 404, 500, malformed
status and JSON, empty and oversized files, repository mismatch, missing pull
authority, public and fork scope, and failed, cancelled, skipped, missing, or
cross-path-incoherent step results. Hosted evidence and tracker creation remain
pending authorization and repair of the external Actions billing/spending block.
