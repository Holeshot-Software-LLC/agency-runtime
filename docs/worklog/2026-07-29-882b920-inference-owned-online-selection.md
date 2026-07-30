---
title: "Worklog detail: Keep online workforce selection inference-owned"
status: active
category: worklog
created: 2026-07-29
updated: 2026-07-29
tags: [workforce, inference, routing, selection, offline]
related:
  - docs/decisions/0087-inference-decides-from-a-relevance-shortlist.md
  - docs/decisions/0088-deterministic-typed-recall-offline-floor.md
  - docs/roadmap/issue-AR-199-restore-codex-workforce-evidence.md
  - docs/roadmap/handoffs/issue-AR-199.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: worklog
commit: 882b920
short: 882b920
date: 2026-07-29
pr: null
related_issues:
  - docs/roadmap/issue-AR-199-restore-codex-workforce-evidence.md
---

# Worklog detail: Keep online workforce selection inference-owned

## Purpose

Restore the accepted ADR-0088 contract: inference is the sole specialist
decider whenever a workforce provider is configured, while deterministic typed
staffing remains available only as the visibly stamped no-provider floor.

## Approach

The configured-provider path no longer builds a deterministic team before the
recruiter or skips the recruiter when that team is accepted. Every fresh online
route runs the planner and recruiter. Nomination parsing no longer promotes role
anchors when inference names no eligible required specialist, and it no longer
reorders the inference ranking around an anchor. Typed recall still exposes the
broad eligible roster, and deterministic verification still vetoes unsafe or
insufficient nominations without choosing their replacement.

## Challenges encountered

The implementation and its tests had normalized a hybrid design even though
ADR-0088 explicitly prohibited it. One branch called the recruiter only after
deterministic staffing failed; another described anchor promotion as a safety
fallback after inference. A temporary architecture anchor proposed during the
ordinary-trace repair would have deepened that violation, so commit `6ca745d`
removed it before this repair was published.

## Decisions and alternatives

Implement the already accepted ADR rather than create a new decision. Preserve
contract-driven recall and safety validation because they bound what inference
may see and execute; remove only their authority to appoint or reorder workers
online. Preserve the ADR-0088 offline floor unchanged when no provider is
configured.

## Verification

- Inference, selection, staffing, routing, hiring, and child-coordination tests
  pass 175 tests with one platform skip and one expected xfail.
- Focused Ruff, formatting, and diff checks pass.
- The named fast repository spine remains the next checkpoint before merge.

## Follow-ups

Complete AR-199 fast verification, merge and exact-install the repair, then run
one bounded ordinary isolated-profile Codex product proof.
