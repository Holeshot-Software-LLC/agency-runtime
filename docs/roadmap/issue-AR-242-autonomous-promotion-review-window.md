---
title: "AR-242: Autonomous promotion with review window (slice 6 of AR-235)"
status: done
category: roadmap
created: 2026-08-04
updated: 2026-08-12
tags: [workforce, promotion, hiring, sub-issue]
related:
  - docs/roadmap/issue-AR-235-autonomous-gap-hiring-with-isolated-security-review.md
  - agency_runtime/core/workforce/promotion.py
  - agency_runtime/core/store/workforce.py
  - agency_runtime/core/config_defaults.yaml
  - docs/decisions/0157-automatically-promote-host-verified-contractors.md
supersedes: []
superseded_by: null
type: issue
epic: routing
issue_id: AR-242
priority: p0
tracker_url: "https://github.com/Holeshot-Software-LLC/agency-runtime/issues/251"
depends_on: []
blocks: [AR-252]
---

# AR-242: Autonomous promotion with review window (slice 6 of AR-235)

## Problem

AR-235 §6 enables autonomous promotion. `auto_promote_successes: 0` keeps
promotion human-controlled by default, which is incompatible with autonomous
24/7 operation. A contractor with N independently verified successful
assignments is a known-good asset that does not need a human in the loop.

## Current state

> **Corrected 2026-08-12.** The bullets below describe the pre-implementation
> state retained for provenance. Commit `f85074f` set the defaults to three
> successes and seven days and wired the review-window projection. AR-256 owns
> reconciliation of the unchecked acceptance boxes; AR-252 owns the still-
> missing live host-backed acceptance path.

- `auto_promote_successes: 0` (`config_defaults.yaml`) — automatic promotion
  is off.
- `contractor_review_days: 30` — not referenced in the runtime logic; only a
  config field.
- `promotion_readiness` in `promotion.py` computes eligibility from verified
  successes but has no review-window concept.
- `_auto_promote_if_ready` in the store calls `promotion_readiness` and
  promotes when eligible.

## Approach

- `auto_promote_successes: 3` (was 0) — three independently verified
  successful assignments auto-promote a contractor to employee.
- `contractor_review_days: 7` (was 30) — for contractors younger than the
  review window, auto-promotion is suppressed. The window is computed
  per-contractor from `created_at`.
- `promotion_readiness` accepts `review_window_days` and `created_at`. When
  the contractor is within the window, `eligible_for_automatic_promotion`
  is False and `in_review_window` is True.
- The store's `_auto_promote_if_ready` passes `review_window_days` from
  config. The CLI and dashboard projections also pass it.

## Dependencies

- None new; builds on the existing promotion evidence path.

## Acceptance

- [x] `auto_promote_successes: 3` and `contractor_review_days: 7` are the
      new defaults.
- [x] A contractor with 3 verified successes is auto-promoted when past the
      review window.
- [x] A contractor within the review window is not auto-promoted even with
      3 verified successes; the readiness projection shows
      `in_review_window: true`.
- [x] The review window is computed per-contractor from `created_at`.
- [x] Focused tests cover: auto-promote past window, suppression within
  window, release after expiry.

These checks prove the policy implementation and simulation only. AR-252
remains P0 because production outcomes do not yet provide the independent,
host-backed acceptance evidence needed to trigger automatic promotion live.
