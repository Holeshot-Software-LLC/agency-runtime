---
title: "Worklog detail: fix(routing): fail regulated assurance gaps closed"
status: active
category: worklog
created: 2026-07-27
updated: 2026-07-27
tags: [routing, workforce, assurance, safety]
related:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-121-inference-planning-and-staffing.md
  - docs/roadmap/issue-AR-125-workforce-and-one-shot-evaluation.md
  - docs/roadmap/issue-AR-179-fail-named-regulated-assurance-gaps-closed.md
  - docs/decisions/0103-bind-named-regulated-assurance-to-typed-staffing.md
supersedes: []
superseded_by: null
type: worklog
commit: c2ebfc6
short: c2ebfc6
date: 2026-07-27
pr: null
related_issues:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-121-inference-planning-and-staffing.md
  - docs/roadmap/issue-AR-125-workforce-and-one-shot-evaluation.md
  - docs/roadmap/issue-AR-179-fail-named-regulated-assurance-gaps-closed.md
---

# Worklog detail: fix(routing): fail regulated assurance gaps closed

## Purpose

Prevent a named regulated-assurance request from being accepted by a generic
team after inference erases the standard from typed staffing requirements.

## Approach

Derive bounded named-standard capabilities only in high-assurance context,
attach them to independent review during deterministic enrichment, and reject
plans that omit the review or requirement. Exact governed contract coverage is
required; otherwise the verifier exposes a staffing gap.

## Challenges encountered

The live failure was not a verifier arithmetic bug. The planner had already
removed DO-178C scope, so every remaining generic requirement appeared covered.
The repair therefore belongs at the request-to-plan boundary while preserving
the existing verifier and hiring contracts.

## Decisions and alternatives

ADR-0103 rejects prompt-specific avionics routing and semantic substitution by
generic reviewers. Ordinary format references remain outside the rule unless
the request establishes high-assurance scope.

## Verification

- 57 focused compact-intent and staffing-verifier tests passed.
- 52 inference/selection tests passed with 1 skip and 1 expected failure.
- 12 dynamic-hiring tests passed.
- Ruff lint/format and documentation validation passed for 446 Markdown files.
- GitHub issue #154 exists with `epic:routing` and `needs-grillme` labels.

## Follow-ups

Run one post-checkpoint live route. A qualified worker may be selected; absent
one, the request must abstain and expose the governed gap.
