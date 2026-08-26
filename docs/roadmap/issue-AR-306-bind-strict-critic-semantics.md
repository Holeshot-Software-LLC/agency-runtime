---
title: "AR-306: Bind strict critic to verified staffing semantics"
status: in_progress
category: roadmap
created: 2026-08-26
updated: 2026-08-26
tags: [workforce, inference, critic, validation]
related:
  - CHANGELOG.md
  - docs/roadmap/issue-AR-297-complete-unattended-container-bootstrap.md
  - docs/roadmap/issue-AR-305-normalize-planner-novelty-absence.md
  - docs/roadmap/handoffs/issue-AR-297.md
  - agency_runtime/core/workforce/inference.py
  - tests/test_workforce_inference.py
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: workforce
issue_id: AR-306
priority: p0
tracker_url: null
depends_on: [AR-305]
blocks: [AR-297]
---

# AR-306: Bind strict critic to verified staffing semantics

## Problem

The strict staffing critic received a plan, proposal, verifier result, and
selected contracts, but not the configured confidence/margin thresholds or an
explicit statement that only `selected` workers compose the team. In a live
AR-297 turn it vetoed a single Accessibility Auditor at confidence 1.0 and the
exact minimum margin as both `unsupported-confidence` and
`unsafe-composition`, despite the hard verifier accepting the team.

## Current state

- Post-AR-305 live inference applies planner, two embedding batches, reranker,
  and recruiter, then stops only at the strict critic.
- A non-activating strict-pipeline diagnostic records the exact plan,
  recruiter proposal, verifier-safe selected team, and critic codes.
- The candidate supplies a bounded pre-execution critic contract with the exact
  confidence and margin thresholds, selected-only composition semantics, and
  the categories that remain unselected.
- The first live confirmation made both critic attempts approve, but each
  attached reason codes and was correctly rejected with
  `critic_approval_reasons_present`. The candidate now states the conditional
  response rule in both the critic control document and system prompt.
- The critic system explicitly forbids demanding completed task evidence and
  preserves semantic wrong-neighbor, lifecycle-assurance, selected-composition,
  and confidence veto authority.
- Focused planning, inference, and selection coverage passes 158 tests with one
  expected skip; changed-file static checks pass.
- Tracker creation is prohibited by the active task.

## Approach

Keep the independent critic and its ability to veto. Make its decision inputs
complete and unambiguous: label the review as pre-execution, state the hard
facts already verified by deterministic policy, identify the only categories
that compose the selected team, and include the exact configured thresholds.
Do not auto-approve, discard a veto, change a model route, or weaken validation.

## Dependencies

- AR-305 removes the false capability that previously prevented a verifier-safe
  proposal from reaching the critic.
- Strict workforce assurance and its existing call budget remain unchanged.
- Tracker creation requires separate outward-write authorization.

## Acceptance

- [x] The critic receives exact configured confidence and margin thresholds.
- [x] The critic distinguishes selected workers from every unselected category.
- [x] The critic is told this is pre-execution staffing and cannot demand task
      output that does not exist yet.
- [x] Independent semantic veto authority remains intact.
- [x] Approval requires an empty reason-code array and rejection requires one
      or more bounded hyphenated reason codes.
- [x] Focused warning-strict tests and changed-file static checks pass.
- [ ] A live strict/additive preflight approves the correct team and loads its
      complete governed prompt.
- [ ] A same-repository tracker is created and linked after explicit
      authorization.
