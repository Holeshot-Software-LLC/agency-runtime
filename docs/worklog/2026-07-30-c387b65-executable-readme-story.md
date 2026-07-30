---
title: "Worklog detail: docs(product): lock the executable README story"
status: active
category: worklog
created: 2026-07-30
updated: 2026-07-30
tags: [product, dashboard, inference, activation, automation]
related:
  - docs/roadmap/issue-AR-204-reconcile-readme-story-contract.md
  - docs/decisions/0117-unify-owner-control-authority.md
  - docs/decisions/0118-require-inference-owned-staffing.md
  - docs/decisions/0119-separate-native-trust-modes-from-activation-proof.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: worklog
commit: c387b6503813b7d34120f2406f9e8fdd965edd6d
short: c387b65
date: 2026-07-30
pr: null
related_issues:
  - docs/roadmap/issue-AR-204-reconcile-readme-story-contract.md
---

# Worklog detail: docs(product): lock the executable README story

## Purpose

Freeze one product contract before resuming implementation so the README,
security authority, inference behavior, native activation, response evidence,
dashboard proof, and autonomous installation cannot drift independently again.

## Approach

Created AR-204 and three focused decisions. ADR-0117 gives normal owner CLI and
the owner dashboard equivalent control authority while keeping broker, hook,
and MCP credentials read-only. ADR-0118 removes deterministic specialist
selection. ADR-0119 separates attended and explicit autonomous trust modes from
behavioral activation. README now states those boundaries as the acceptance
story rather than preserving contradictory historical behavior.

## Challenges encountered

The preceding decision chain partially superseded dashboard opt-in semantics
while retaining unrelated read-only clauses, and the production code still
contains complete mutation implementations behind blanket gates. The new
decisions therefore restate the whole current contract instead of attempting
another partial supersession.

## Decisions and alternatives

The owner clarified that dashboard service open may ensure service health, the
dashboard is optional but default-installed, substantive staffing must fail
without inference, transparent dashboard authentication remains acceptable,
and both human and autonomous owner execution must work. Those choices are
recorded in ADR-0117 through ADR-0119.

## Verification

- Documentation metadata check passed for 558 files.
- Policy availability and worklog checks passed.
- Documentation validation passed for 558 files.
- Tracker #189 was created with `bug` and `epic:product` labels.
- Strict tracker parity exposed pre-existing unrelated tracker gaps; AR-204's
  local ID, URL, title, and label are present.

## Follow-ups

Implement and prove every AR-204 acceptance item before resuming the exact-build
README product trial.

