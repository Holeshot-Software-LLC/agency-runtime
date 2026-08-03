---
title: "AR-226: Repair automatic pull-request verification"
status: in_progress
category: roadmap
created: 2026-08-03
updated: 2026-08-03
tags: [bug, ci, release, security, testing]
related:
  - .github/workflows/ci.yml
  - .github/workflows/dependency-review.yml
  - tests/runtime_support.py
  - tests/test_ci_session_pair.py
  - tests/test_prepare_ci_runtime.py
  - tests/test_release_packaging.py
  - docs/roadmap/issue-AR-203-prove-product-canary-write-and-activation.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: release
issue_id: AR-226
priority: p0
tracker_url: null
depends_on: []
blocks: []
---

# AR-226: Repair automatic pull-request verification

## Problem

PR #235 exposed three automatic verification defects unrelated to its proven
product outcome. The Linux quality job runs executable-namespace tests through
the hosted tool cache, whose parent namespace is intentionally rejected. The
dashboard resource ceiling predates the current audited product-proof UI. The
dependency-review classifier rejects an exact authenticated repository response
when GitHub omits its optional `permissions` projection, even though the
successful response already proves repository read authority.

These defects make a locally green, independently proven product change appear
unmergeable and prevent all downstream automatic jobs from running.

## Current state

The bounded repair makes the two real process-controller tests use the OS-owned
POSIX interpreter rather than a replaceable hosted-tool-cache path, raises the
dashboard aggregate ceiling from 268 KiB to a narrow
300 KiB bound above the observed 296,619-byte audited payload, and validates
repository identity from the authenticated 200 response without requiring an
optional response field. The focused workflow, runtime, dependency, and release
contract suite passes 185 tests under warning-strict mode.

## Approach

1. Preserve executable namespace enforcement and run real POSIX
   process-controller tests through an OS-owned interpreter.
2. Keep a bounded dashboard resource budget with measured headroom rather than
   removing the package-size assertion.
3. Bind dependency fallback to exact repository identity and the exact expected
   private-repository 403 response without depending on an optional API field.
4. Rerun PR #235's automatic gates and merge only after they pass.

## Dependencies

The repair is required to complete PR #235 but does not change the AR-203 product
proof or reopen its live evaluation.

## Acceptance

- [x] The focused workflow, runtime, dependency, and release tests pass locally.
- [ ] The Linux quality contract runs real process tests with an OS-owned interpreter.
- [ ] The dashboard resource assertion passes while retaining a finite ceiling.
- [ ] Dependency review either runs natively or enters its exact audited fallback.
- [ ] Every automatic PR #235 gate passes before merge.
