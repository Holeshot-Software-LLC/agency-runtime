---
title: "AR-260: Accept verified launch bindings in the outcome canary"
status: in_progress
category: roadmap
created: 2026-08-20
updated: 2026-08-20
tags: [canary, outcomes, native-child, evidence, claude, AR-119]
related:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-252-record-verified-acceptance-outcomes.md
  - docs/roadmap/issue-AR-255-inference-owned-host-proven-child-staffing.md
  - docs/roadmap/AR-119-9685a16d-accepted-outcome-evidence.md
  - docs/roadmap/handoffs/issue-AR-119.md
  - docs/decisions/0156-host-artifacts-prove-native-child-delivery.md
  - agency_runtime/core/outcome_canary.py
  - tests/test_accepted_outcome_canary.py
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: observability
issue_id: AR-260
priority: p0
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/307
depends_on: [AR-252, AR-255]
blocks: [AR-119]
---

# AR-260: Accept verified launch bindings in the outcome canary

## Problem

The exact-main Claude accepted-outcome draw for pair `9685a16d...` completed,
staffed the existing TypeScript contractor, verified producer and verifier host
artifacts, and recorded one accepted outcome. The canary report still failed
closed because `_route_projection` accepted only `child_id` bindings and read
the route's binding ID as the child ID. Claude's supported prelaunch contract
binds the route by `launch_id`; the verified delivery row records the actual
child ID separately after launch.

## Current state

- The content-free live facts and evidence limits are recorded in
  `AR-119-9685a16d-accepted-outcome-evidence.md`.
- Both route and delivery rows agree on host, parent session/trace, launch ID,
  binding kind, binding ID, nonce, decision ID, cards, and provider receipt.
- The only rejecting condition is the canary reporter's local assumption that
  every exact binding must be `child_id`.
- Tracker [#307](https://github.com/Holeshot-Software-LLC/agency-runtime/issues/307)
  is open with `epic:observability`.

## Approach

Project the actual child identity from the independently verified delivery
receipt. Accept only two exact binding shapes:

1. `child_id`, where route binding ID equals the verified delivery child ID;
2. `launch_id`, where route binding ID equals the exact route launch ID.

All existing cross-row equality, verified-delivery, digest, provider, card, and
parent-correlation checks remain mandatory. Unknown or mismatched binding kinds
continue to fail closed.

## Dependencies

- AR-252 owns accepted-outcome collection and automatic promotion evidence.
- AR-255 owns inference-selected, host-proven native child staffing.
- ADR-0156 requires independent host-authored delivery proof.

## Acceptance

- [x] Historical exact `child_id` bindings still pass.
- [x] Exact Claude `launch_id` bindings report the verified delivery child ID.
- [x] Unknown binding kinds fail closed.
- [ ] Focused and proportional local gates pass on a clean recovery pair.
- [x] Required tracker issue is created after explicit owner authorization.
- [ ] A reviewed PR reaches main and all three Windows harnesses are reinstalled.
- [ ] One later authorized Claude draw passes the reporter without weakening
      artifact verification; this issue itself moves no matrix cell.
