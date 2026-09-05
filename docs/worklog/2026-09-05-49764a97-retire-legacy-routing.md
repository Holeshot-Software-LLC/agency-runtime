---
title: "Retire AR-115's superseded routing proposal"
status: active
category: worklog
created: 2026-09-05
updated: 2026-09-05
tags: [backlog, routing, supersession, evidence]
related:
  - docs/roadmap/issue-AR-115-live-routing-trust.md
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-125-workforce-and-one-shot-evaluation.md
  - docs/roadmap/AR-404-oldest-first-reconciliation-20260905.md
  - docs/decisions/0222-retire-superseded-live-routing-contract.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: worklog
commit: 49764a978b1c023384fc77d92218e2cc616e4217
short: 49764a97
date: 2026-09-05
pr: https://github.com/Holeshot-Software-LLC/agency-runtime/pull/690
related_issues:
  - docs/roadmap/issue-AR-115-live-routing-trust.md
---

# Worklog: retire superseded live-routing proposal

## Purpose

Apply the owner's oldest-first cleanup order to the oldest unfinished item,
AR-115, without claiming the still-broken ordinary session is healthy.

## Approach

ADR-0222 retires its heuristic-selection/six-field-header design and supersedes
ADR-0078. Existing ADR-0118 and implemented AR-357 govern the current behavior.
AR-119 explicitly absorbs the surviving live obligation; AR-125 retains
independent evaluation. All historical checkbox states remain unchanged.

## Challenges encountered

The first documentation validation exposed the reciprocal historical AR-116
dependency. It is now a provenance link rather than an active prerequisite;
AR-116's old transport acceptance and present limitations remain untouched.
Current staffing reports a missing credential and no specialist, while header
evidence is unreadable. Those facts prevent a live-success claim, not the
retirement of an incompatible historical design. No credential was inspected
or changed for this package, and no new live/provider call was made.

## Decisions and alternatives

See ADR-0222. Reimplementing heuristic fallback would contradict current
selection authority; marking old live gates satisfied would be false.
Retirement removes the duplicate plan while keeping the product outcome open.

## Verification

- Focused routing/header/credential/resident-manager and docs/tracker: 183 pass,
  19.11s. Fresh named fast spine: 1075 pass/three existing skips, 68.74s.
- Configured UI command: 138 pass, 96.92/86.62/95.71 product coverage.
- Ruff check/format, metadata, policy availability, worklog and strict docs pass.
- Tracker audit permits only the expected AR-115 open-complete mismatch before
  its merge and authorized not-planned closure; every other parity check passes.
- Runtime/test/tool source is unchanged from e5662d91 and installed 0309f251.
  Prior routing/184-mutation and installed eight-check smoke evidence is not a
  new live trial. No Windows, exhaustive matrix or workflow dispatch.

## Follow-ups

Merge this record package, close tracker #127 as not planned, then review AR-119
next. Keep the legacy-local and external-tracker counts separate. AR-119/AR-125
remain open until their actual current evidence obligations are fulfilled.
