---
title: "Worklog detail: docs(evaluation): defer one-shot applications post-production"
status: active
category: worklog
created: 2026-07-27
updated: 2026-07-27
tags: [evaluation, release, roadmap]
related:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-125-workforce-and-one-shot-evaluation.md
  - docs/roadmap/issue-AR-178-evaluate-one-shot-applications-post-production.md
  - docs/decisions/0102-defer-one-shot-application-evaluation.md
supersedes: []
superseded_by: null
type: worklog
commit: 6cb8406
short: 6cb8406
date: 2026-07-27
pr: null
related_issues:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-125-workforce-and-one-shot-evaluation.md
  - docs/roadmap/issue-AR-178-evaluate-one-shot-applications-post-production.md
---

# Worklog detail: docs(evaluation): defer one-shot applications post-production

## Purpose

Move the expensive six-application study out of the production critical path
without weakening Agency's live selection, participation, host, artifact, or
comparative-outcome evidence.

## Approach

ADR-0102 makes complete one-shot applications a P2 post-production evaluation
owned by AR-178 and explicitly non-blocking for AR-119, AR-125, production GO,
and release. AR-125 now owns workforce selection, matched Agency-on/off value,
five-host canaries, and current Windows/Linux artifacts. Tracker issues #132 and
#138 were updated and #153 was created for AR-178.

## Challenges encountered

The old criterion appeared in the live tracker, canonical roadmap issue,
acceptance summary, and live-gates runbook. All active contracts had to change
together so historical wording could not remain an accidental release gate.

## Decisions and alternatives

The evaluator implementation remains in the product. Deleting it was rejected
because the deferred study still has value after launch.

## Verification

- Documentation metadata and policy checks passed for 443 Markdown documents.
- Documentation validation and `git diff --check` passed.
- Live tracker reads confirmed #132 and #138 are open with the revised scope and
  #153 is open with `epic:testing` and `needs-grillme` labels.

## Follow-ups

AR-119 and AR-125 retain their fresh live outcome, host, and artifact gates.
AR-178 begins only after AR-119 production readiness.
