---
title: "AR-252: Record host-evidenced, independently verified outcomes for automatic promotion"
status: open
category: roadmap
created: 2026-08-05
updated: 2026-08-12
tags: [workforce, promotion, evidence, native-child, outcomes, critical-path]
related:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-242-autonomous-promotion-review-window.md
  - docs/roadmap/issue-AR-255-inference-owned-host-proven-child-staffing.md
  - docs/decisions/0118-require-inference-owned-staffing.md
  - docs/decisions/0156-host-artifacts-prove-native-child-delivery.md
  - docs/decisions/0157-automatically-promote-host-verified-contractors.md
  - agency_runtime/core/child_delivery_evidence.py
  - agency_runtime/core/store/workforce.py
  - agency_runtime/core/store/native_child.py
  - agency_runtime/core/workforce/promotion.py
supersedes: []
superseded_by: null
type: issue
epic: workforce
issue_id: AR-252
priority: p0
tracker_url: null
depends_on: [AR-180, AR-242, AR-255]
blocks: [AR-119, AR-253]
---

# AR-252: Record host-evidenced, independently verified outcomes for automatic promotion

## Problem

The automatic contractor-to-employee policy is implemented, but its live
evidence path is dormant. Native child termination records an `assignment`
outcome without independent acceptance evidence, so production work cannot
satisfy `promotion_readiness` or trigger `_auto_promote_if_ready`.

The former proposal depended on retired Job B plan rows, assurance units, and
consumed activation receipts. Restoring that transport would contradict the
current host-spawned, just-in-time architecture.

## Current state

AR-242 set the three-success and seven-day review-window policy. Store code can
validate acceptance evidence and perform automatic promotion atomically, but no
current host-backed producer/verifier correlation emits the required event.
Agency-authored assignment rows alone are not proof of successful work.

## Approach

Build an outcome envelope from artifacts the native host wrote. Those artifacts
prove the producer/verifier children, delivered card hashes, artifact digest,
and correlation; they do not prove semantic correctness. A distinct governed
verifier selected by inference establishes semantic acceptance through its
verdict bound to that exact artifact. Store receipts remain a derived audit
index, not the delivery authority.

Evaluate promotion in the same transaction that persists the validated
acceptance. Keep the existing three-success threshold and per-contractor review
window. Do not depend on Job B, model-authored headers, Agency-only lifecycle
rows, or a shared producer/verifier identity.

## Dependencies

- AR-255 must establish inference-owned card choice and host-authored delivery
  proof before an outcome can be attributed to a specialist.
- AR-242 supplies the existing threshold and review-window implementation; its
  unchecked acceptance record is reconciled under AR-256.

## Acceptance

- [x] A host-backed producer artifact plus a distinct, inference-selected
      verifier's host-backed artifact and bound accepted verdict records exactly
      one acceptance event.
- [x] Missing, ambiguous, replayed, Agency-only, shared-identity, or rejected
      evidence records no acceptance and reports a bounded reason.
- [x] Three distinct accepted outcomes automatically promote an eligible
      contractor after its review window with `actor="promotion-policy"` and
      the exact evidence manifest; no operator action is required.
- [x] Replay and concurrent finalization cannot duplicate an outcome or
      promotion.
- [x] Migrate promotion validation and readiness from retired work-unit and
      consumed-activation-receipt identities to the host child, card hash,
      artifact digest, verifier decision, and verdict identities above.
- [ ] Live evidence proves the path through at least Claude and Codex before
      AR-119 can close.
- [ ] AR-253 proves the same accepted-outcome and automatic-promotion behavior
      on ZCode, Hermes, and OpenClaw; an unavailable supported host remains
      unproven and blocks AR-119.

## What the checked boxes do and do not mean

The five checked items are the host-free half: the rule that decides what may
count, the recorder that applies it, and the readiness migration. They are
proven by source and simulation in `agency_runtime/core/workforce/acceptance.py`
and `tests/test_accepted_outcomes.py`, which runs in CI.

They are not proof that the path runs. No host has yet produced a real envelope:
the producer and verifier proofs come from the sealed
`agency.host-child-delivery-proof.v1` projection, and in every case above they
are constructed by the test rather than collected from a Claude transcript or a
Codex rollout. The remaining two items are exactly that gap, and until they
close, the runtime can accept an outcome that nothing yet offers it.

The collector seam is `agency_runtime/core/child_delivery_evidence.py`, whose
`_host_child_delivery_projection` already emits the accepted proof shape for a
verified delivery. What is missing is the step that pairs one producer proof
with one verifier proof and that verifier's verdict, which is where the live
work starts.
