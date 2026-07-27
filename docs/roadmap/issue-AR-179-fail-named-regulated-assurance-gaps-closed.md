---
title: "AR-179: Fail named regulated-assurance staffing gaps closed"
status: in_progress
category: roadmap
created: 2026-07-27
updated: 2026-07-27
tags: [routing, workforce, safety, assurance, contractors]
related:
  - docs/decisions/0103-bind-named-regulated-assurance-to-typed-staffing.md
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-121-inference-planning-and-staffing.md
  - docs/roadmap/issue-AR-125-workforce-and-one-shot-evaluation.md
  - docs/analysis/2026-07-26-production-readiness-review.md
supersedes: []
superseded_by: null
type: issue
epic: routing
issue_id: AR-179
priority: p0
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/154
depends_on: [AR-121]
blocks: [AR-119, AR-125]
---

# AR-179: Fail named regulated-assurance staffing gaps closed

## Problem

A live DO-178C avionics-assurance request was accepted with only generic
onboarding, test-results, and code-review workers. Inference organized useful
work units but omitted the named standard from their typed requirements, so the
deterministic verifier had no missing requirement from which to declare a gap.

## Current state

The local compiler now derives bounded named-standard assurance requirements,
binds them to independent review, and refuses to let generic review coverage
satisfy them. Focused intent, staffing, inference, selection-safety, and dynamic-
hiring tests pass. One fresh live confirmation remains after the clean
checkpoint.

## Approach

Recognize explicit named standards only when the request establishes high-
assurance context, while treating intrinsically regulated standards as such.
Compile each standard into a normalized capability on independent review.
Require exact governed contract coverage; otherwise staffing must abstain and
expose a hireable gap. Preserve ordinary format references such as ISO 8601.

## Dependencies

AR-121 owns plan-first typed staffing. AR-119 and AR-125 cannot close while a
regulated request can be accepted by an unqualified generic team.

## Acceptance

- [x] Named high-assurance standards survive inference as typed requirements.
- [x] Plans that omit the requirement or independent review fail closed.
- [x] Generic reviewers cannot cover the requirement; an explicitly capable
  governed contract can.
- [x] Ordinary non-assurance standards references do not create false gaps.
- [x] Focused compiler, verifier, inference, safety, and hiring tests pass.
- [ ] A fresh live route abstains or declares a gap unless an explicitly
  qualified governed worker exists.
