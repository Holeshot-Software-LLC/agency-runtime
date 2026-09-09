---
title: "AR-425: Preserve rejected planner context and semantic failure identity"
status: in_progress
category: roadmap
created: 2026-09-09
updated: 2026-09-09
tags: [workforce, planner, reliability]
related:
  - docs/decisions/0243-supply-rejected-plans-as-untrusted-repair-data.md
  - docs/decisions/0132-fund-one-repair-per-workforce-inference-stage.md
  - docs/roadmap/issue-AR-404-evidence-led-backlog-completion.md
  - docs/roadmap/issue-AR-423-preserve-claude-hook-specialist-context.md
  - docs/worklog/2026-09-09-planner-repair-context.md
supersedes: []
superseded_by: null
type: issue
epic: reliability
issue_id: AR-425
priority: p1
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/820
depends_on: []
blocks: []
---

# AR-425: Preserve rejected planner context and semantic failure identity

## Problem

The planner repair prompt requires preservation of necessary valid units but its
stateless provider call omits the rejected answer. Most parser failures also lose
their specific identity in the content-free terminal receipt. Claude trace
be4757dc-c14f-4e39-b366-bdfa2ef0ae40 rejected a missing correctness review and
then an unknown semantic error; the exact second failure cannot be recovered.

## Current state

A new two-call planner-only diagnostic reproduces the missing independent
correctness review; its one repair succeeds in33.937s total. It uses the current
roster and canonical Claude capabilities without the original correlated native
turn context. It is neither exact replay nor native acceptance, and does not
establish the original second rejection's cause. Evidence is retained in
`evidence/AR-425-planner-diagnostic-20260909.json`.

The real orchestration regression fails on base e3090882 with missing
rejected_plan_untrusted. The candidate supplies bounded rejected data only to the
planner's existing repair. Five known parser identities survive failure projection;
unknown text remains generic and content-free. Focused143tests pass. No provider,
model, budget, plan validator, recruiter or critic policy changes.

## Approach

Provide the complete bounded rejected object as explicitly untrusted data in the
same planner repair request. Never accept it as a plan or instructions. Validate
the replacement normally and retain the existing two-attempt and total-call caps.
Map only exact runtime-owned parser errors to closed receipt reason codes.

## Dependencies

AR-404 owns five-host reliability. AR-423 owns native Claude full-card delivery.
Their remaining gates cannot be closed from deterministic planner tests.

## Acceptance

- [ ] Reproduce the missing rejected-plan context through real orchestration.
- [ ] Supply bounded untrusted planner repair data while preserving rejection,
      independent assurance, replacement validation and existing call limits.
- [ ] Retain specific known semantic failure identities without rejected content
      in terminal receipts; unknown errors remain generic.
- [ ] Pass focused and required production checks and record a bounded live
      planner/native comparison with failures and exact limitations preserved.
