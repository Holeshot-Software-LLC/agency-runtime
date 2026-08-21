---
title: "Worklog detail: Accept verified launch bindings in the outcome canary"
status: active
category: worklog
created: 2026-08-20
updated: 2026-08-20
tags: [AR-119, AR-252, AR-260, canary, native-child, evidence]
related:
  - docs/worklog/README.md
  - docs/roadmap/AR-119-9685a16d-accepted-outcome-evidence.md
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-252-record-verified-acceptance-outcomes.md
  - docs/roadmap/issue-AR-260-accept-verified-launch-bindings-in-outcome-canary.md
  - docs/decisions/0156-host-artifacts-prove-native-child-delivery.md
supersedes: []
superseded_by: null
type: worklog
commit: 95356cfa8b214d784e63c3d3da2ccd87e06fa5c5
short: 95356cfa
date: 2026-08-20
pr: null
related_issues:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-252-record-verified-acceptance-outcomes.md
  - docs/roadmap/issue-AR-260-accept-verified-launch-bindings-in-outcome-canary.md
---

# Worklog detail: Accept verified launch bindings in the outcome canary

## Purpose

The first exact-main Claude accepted-outcome draw completed the native producer
and verifier deliveries and recorded an accepted outcome, but the final canary
report rejected the projection. The reporter assumed every route was bound by
child ID even though Claude's supported prelaunch contract binds by launch ID
and learns the host child ID later from the delivery artifact.

## Approach

The reporter now projects the child identity from the independently verified
delivery receipt. It accepts either an exact child-ID binding or an exact,
bounded launch-ID binding. Existing cross-row equality checks for decision,
host, parent, launch, binding, nonce, cards, digests, and applied provider remain
mandatory.

## Challenges encountered

A naive launch-binding predicate could accept two missing values as equal. The
implementation therefore requires both bounded launch and binding identifiers
to be present before admitting that shape. Focused regression coverage names
the missing-launch and unknown-binding failures explicitly.

## Decisions and alternatives

The repair does not reinterpret Store rows, infer a child from a launch ID, or
relax host-artifact verification. It uses the delivery's host-observed child ID
and rejects every binding kind outside the two supported exact shapes. Provider
routing, recruiter behavior, staffing selection, hiring, and retry policy are
unchanged.

## Verification

- Focused warning-strict outcome-canary tests: 14 passed.
- Widened accepted-outcome collector, canary, and child-delivery tests: 84
  passed.
- Ruff check and format, metadata, policy availability, and committed-whitespace
  checks passed before the ledger update.
- Documentation validation reached only the expected missing-ledger boundary;
  the following ledger commit records this commit and exact-main merge
  `06f10171`.
- No additional provider call, host CLI, installation, or hosted workflow ran.

## Follow-ups

- [AR-260](../roadmap/issue-AR-260-accept-verified-launch-bindings-in-outcome-canary.md):
  pass proportional gates, publish through a reviewed skip-CI PR, reinstall
  exact main, and run one bounded Claude proof without retry.
- [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md): after the
  reporter is live-proven, continue the authorized staffing, genuine-hiring,
  dashboard-parity, and Linux-handoff sequence.
