---
title: "AR-125: Prove workforce selection and one-shot application outcomes"
status: open
category: roadmap
created: 2026-07-21
updated: 2026-07-21
tags: [evaluation, testing, portability, applications]
related:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/decisions/0080-plan-before-recruiting-from-the-whole-workforce.md
  - docs/decisions/0082-schedule-assurance-by-artifact-lifecycle.md
supersedes: []
superseded_by: null
type: issue
epic: testing
issue_id: AR-125
priority: p0
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/138
depends_on: [AR-120, AR-121, AR-122, AR-123, AR-124]
blocks: []
---

# AR-125: Prove workforce selection and one-shot application outcomes

## Problem

Selection activity and unit tests do not prove that Agency assembles correct
teams or helps each host deliver complete, portable, production-quality apps.

## Current state

Routing corpora, coverage gates, host canaries, and artifact smoke tests exist,
but they do not yet cover every workforce contract or representative complete
applications with independent integration and release verification.

## Approach

Add independent per-worker semantic cases, pairwise composition properties,
meaningful lifecycle teams, configured-inference corpora, six product-level
applications, installed artifacts, five-host contracts (Codex, Claude, Hermes,
OpenClaw, and ZCode), and Agency-on/off trials.

## Dependencies

All preceding AR-119 slices provide the behavior this evidence must grade.

## Acceptance

- [ ] Every worker passes positive, hard-negative, qualifier, shadow, and eligibility cases.
- [ ] Pairwise invariants and curated lifecycle teams pass.
- [ ] All representative one-shot applications pass outcome-based grading.
- [ ] Windows/Linux artifacts and all five host contracts, including ZCode,
  pass before release.
