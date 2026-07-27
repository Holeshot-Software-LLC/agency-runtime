---
title: "AR-159: Enforce production branch protection"
status: open
category: roadmap
created: 2026-07-27
updated: 2026-07-27
tags: [release, security, github, governance, ci]
related:
  - docs/roadmap/issue-AR-156-restore-cost-bounded-verification.md
  - docs/roadmap/issue-AR-162-collapse-unavailable-codeql-fanout.md
  - docs/roadmap/issue-AR-165-fail-ambiguous-dependency-review-capability-closed.md
  - docs/decisions/0037-layered-pinned-supply-chain-gates.md
  - docs/decisions/0097-gate-expensive-ci-fanout-behind-quality-contracts.md
  - docs/RELEASE_CHECKLIST.md
  - .github/workflows/ci.yml
supersedes: []
superseded_by: null
type: issue
epic: release
issue_id: AR-159
priority: p0
tracker_url: null
depends_on: [AR-156, AR-162, AR-165]
blocks: []
---

# AR-159: Enforce production branch protection

## Problem

The repository defines and tests an aggregate production gate, but GitHub does
not currently require that gate before `main` changes. A maintainer, automation,
or compromised credential can therefore update the release branch without the
reviewed CI contract.

## Current state

A read-only GitHub API audit on 2026-07-27 returned `404 Branch not protected`
for `main` and an empty repository-ruleset collection. The workflow's aggregate
result is therefore advisory hosted evidence, not enforced merge authority.
Current hosted jobs are also rejected before steps by the account's
billing/spending state, so exact successful check names must be re-observed after
that external block is repaired.

## Approach

After explicit authorization for hosted settings, inventory the exact current
check contexts from successful CI, CodeQL, and dependency-review runs. Apply one
repository ruleset or equivalent branch-protection policy to `main` that
requires pull requests and those production checks, blocks force pushes and
deletion, and gives bypass authority only to an explicitly reviewed emergency
role. Read the settings back through the API and test both a compliant merge and
a rejected direct or under-validated update.

## Dependencies

AR-156 must provide current hosted check evidence after GitHub billing/spending
is repaired. ADR-0037 governs the layered supply-chain gates; ADR-0097 governs
the CI aggregate and cost-bounded dependency graph.

## Acceptance

- `main` is covered by a repository ruleset or equivalent branch protection.
- Production updates require a pull request and the exact current aggregate CI,
  CodeQL, and dependency-review checks.
- Force pushes and branch deletion are blocked.
- Any bypass is least-privilege, named, audited, and exercised only through a
  documented emergency path.
- API readback proves the active rule targets `main` and the intended checks.
- A compliant test change can merge, while a direct or missing-check update is
  rejected.
- The tracker issue and local roadmap record have exact URL/state parity.
