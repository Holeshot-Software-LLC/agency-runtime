---
title: "Retain current branch-protection gap"
status: active
category: worklog
created: 2026-09-07
updated: 2026-09-07
tags: [security, governance, ci, backlog]
related:
  - docs/roadmap/issue-AR-159-enforce-production-branch-protection.md
  - docs/roadmap/acceptance/evidence/AR-159-branch-protection-20260907.md
  - docs/decisions/0037-layered-pinned-supply-chain-gates.md
  - docs/decisions/0097-gate-expensive-ci-fanout-behind-quality-contracts.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: worklog
commit: e708c2122884134c0d4824be9fb7a9d743161285
short: e708c212
date: 2026-09-07
pr: null
related_issues:
  - docs/roadmap/issue-AR-159-enforce-production-branch-protection.md
---

# Worklog detail: Current branch-protection audit

## Purpose and approach

Reconcile AR-159 against current read-only settings and source contracts rather
than its July diagnosis. Main remains unprotected with no rulesets including
parents. Current main has zero checks/status contexts; source gates cannot
substitute for hosted enforcement. Retain all seven original criteria and open
status, and give the remaining owner-controlled package an executable sequence.

## Challenges and decisions

Latest CI/repository CodeQL runs are August 31/cancelled, dependency review is
successful only at that old head, and all workflows report active. Missing
current evidence does not establish a billing cause. A second dynamic CodeQL
workflow requires check-identity reconciliation, not an unsolicited settings
change. ADR-0037/0097 remain governing; no new architecture or policy decision.
No branch/account/bypass change, unsafe main probe or manual workflow dispatch.

## Verification

104 focused warning-strict workflow/security cases pass in 3.02s, 16 deselected,
no skips/failures. No product, tests, scripts or workflow bytes differ from
b2ea5946. AR-156 spine/UI/wheel receipts are reused explicitly, not rerun.
Strict docs/tracker, metadata/policy, worklog, Ruff and diff checks pass.
Current counts remain 40 actual trackers plus 89 unfinished legacy records.

## Follow-ups

Publish normally, then AR-160 separately. AR-159 awaits approved enforcement,
named bypass/emergency procedure, current check/app identities and recoverable
positive/negative proof. No isolated acceptance or closure claimed. The required
Codex refresh returned activation-required/unverified trust and mixed projections;
this does not justify unattended retries or verified Agency loading claims.
