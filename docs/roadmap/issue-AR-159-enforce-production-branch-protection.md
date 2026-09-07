---
title: "AR-159: Enforce production branch protection"
status: open
category: roadmap
created: 2026-07-27
updated: 2026-09-07
tags: [release, security, github, governance, ci]
related:
  - docs/decisions/0226-gate-codeql-savings-claims-on-matched-measurements.md
  - docs/roadmap/acceptance/evidence/AR-159-branch-protection-20260907.md
  - docs/roadmap/issue-AR-404-evidence-led-backlog-completion.md
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

The September 7 read-only audit at b2ea5946 confirms this remains relevant:
`main.protected=false`, its protection endpoint returns `404 Branch not protected`,
and the ruleset collection including parents is empty. The workflow's aggregate
result remains advisory rather than enforced merge authority. Current main has
zero check runs and zero legacy status contexts; PR #710 has an empty check
rollup. None of those empty results means checks passed.

The latest listed CI and CodeQL runs are August 31/cancelled. Dependency review
has an August 31 successful job, not current-candidate proof. The workflows are
active. The July 27 billing/spending explanation is historical; this audit does
not establish why current runs are absent. Exact API observations, workflow
inventory, source names and bounded verification are in the
[receipt](acceptance/evidence/AR-159-branch-protection-20260907.md).

Disposition: retain `open`, with the enforcement package `waiting_for_operator`.
No settings, checks, bypasses, permissions, workflow triggers or acceptance
criteria were changed. Local aggregate/security contracts pass 104 cases;
that is not hosted enforcement. This legacy record keeps `tracker_url: null`
under the existing pre-tracker exemption; no duplicate tracker is created.

## Approach

1. Obtain explicit owner approval for hosted enforcement, its bypass identity
   and emergency/rollback procedure. Routine backlog PR authority is not approval
   to alter those settings or deliberately attempt unsafe writes to `main`.
2. Establish current successful PR checks and their producing app identities.
   Re-observe the CI aggregate, CodeQL result and dependency-review contexts;
   source job names are candidates, not sufficient enforcement identifiers.
   Reconcile the separately listed dynamic CodeQL workflow before selecting
   required checks. Do not require each conditional analyzer or manual suite.
3. Apply one approved ruleset or equivalent policy targeting `main`: require
   PRs and the verified production checks, prohibit force pushes and deletion,
   and restrict any bypass to the explicitly reviewed emergency role.
4. Read back the exact target, enforcement, check/app bindings and bypass list.
   Carry out an owner-approved, recoverable positive/negative verification plan
   without destructive branch probes. Record compliant and rejected outcomes.
5. Freeze per-criterion evidence for isolated acceptance before completion.
   Preserve the legacy tracker exemption unless the owner requests its migration.

## Dependencies

AR-156 retains current hosted/topology evidence; its old billing diagnosis needs
fresh confirmation before any account action. AR-162 and AR-165 own the CodeQL
and dependency-review capability contracts. ADR-0037 requires their bounded,
fail-closed capability handling; an unavailable analyzer is not analysis proof.
ADR-0097 governs the aggregate and cost-bounded graph. Optional exhaustive suites
remain manual; no dispatch or new subscription is authorized by this audit.

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
