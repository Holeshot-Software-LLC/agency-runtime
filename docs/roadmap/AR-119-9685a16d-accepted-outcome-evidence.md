---
title: "AR-119 Claude accepted-outcome evidence for pair 9685a16d"
status: active
category: roadmap
created: 2026-08-20
updated: 2026-08-20
tags: [roadmap, evidence, claude, native-child, outcomes, AR-119, AR-252, AR-260]
related:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-252-record-verified-acceptance-outcomes.md
  - docs/roadmap/issue-AR-260-accept-verified-launch-bindings-in-outcome-canary.md
  - docs/roadmap/AR-119-vision-loop-status.md
  - docs/roadmap/handoffs/issue-AR-119.md
  - docs/decisions/0156-host-artifacts-prove-native-child-delivery.md
  - agency_runtime/core/outcome_canary.py
supersedes: []
superseded_by: null
type: reference
issue_id: AR-119
---

# AR-119 Claude accepted-outcome evidence for pair 9685a16d

This package records exactly one Claude draw after PR #306 and exact-main
installation. Store inspection was SQLite read-only and content-free. No retry,
second provider call, matrix promotion, or inferred model prose followed.

## Exact installed candidate

- PR #306 merged as `06f10171dc6614b723eef0a04d6ebbcfb357a63c`
  with tree `5090b4ab3234d4d31e0764b1c7e11b580e6b4e76` and `[skip ci]`.
- Claude, Codex, and ZCode launcher manifests all name runtime digest
  `3951cb3697261b5d80387451a615beaf7699f7899f2b751b42878d35364c69e7`
  from the exact rollout checkout. Status reported zero drift hosts.
- Claude readiness had no unmet prerequisites. Telemetry ran immediately
  before the single 420-second invocation.

## Invocation and Store correlation

- Pair `9685a16db43269c171c6c702aa9322c9`; parent session
  `bf098816-fc07-4b8f-9b4b-88fcf909dfb5`; trace
  `35175ce8-f2f1-45f3-a728-6fa66bd1435e`.
- Claude exited 0 without timeout or truncation. The private collector returned
  `accepted`; the parent run ended `response_invalid` only after the canary
  reporter rejected its final projection.
- Parent decision `47a1f884-9f46-459e-bb45-7491ad1612e4` selected the existing
  `typescript-application-engineer`. No preflight failure receipt exists.
- Producer decision `native-child-9b647501fc5022f38eee934a46f4f22a`
  selected that contractor through the requested `codex-subscription` judge.
- Verifier decision `native-child-1b357eb8bd66970fa0220f7fca939d0b`
  selected `code-reviewer` through the same requested provider.
- The Store contains two independent verified-delivery receipts with distinct
  child IDs and artifact digests, plus acceptance event
  `8bb40357-4228-4ea9-95fd-4e5c54c645cc` for worker
  `54cb1db1-7c55-5d13-9fff-ddb1bd5ca921`, score 1.0.

These rows correlate the in-process host collector's accepted result. The
disposable host artifacts no longer exist after isolated-profile cleanup, so
this record does not substitute Store rows for a retained host artifact or
promote a Rule-4 matrix cell.

## Exact reporter defect

Both verified deliveries use the supported prelaunch shape:

- `binding_kind = launch_id`;
- `binding_id = launch_id = toolu_...`;
- `child_id = a...`, learned independently from the host artifact after launch.

`outcome_canary._route_projection` instead required
`binding_kind == "child_id"`, assigned `route.binding_id` to `child_id`, and
then required that value to equal `delivery.child_id`. Every other exact
provider, digest, card, parent, launch, and delivery check passed. The top-level
canary therefore reported `accepted-outcome route, delivery, or Store result
projection was invalid` despite the accepted host collection.

AR-260 repairs only that reporter assumption. This draw proves the existing
contractor was staffed and an acceptance was recorded; it does not prove a new
hire, exercise AR-259's failure receipt, justify a retry before publication, or
move any matrix cell.
